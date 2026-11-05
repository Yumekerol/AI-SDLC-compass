from __future__ import annotations

import json
import logging
import re

from collections import Counter
from pathlib import Path
from typing import Any

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

from .__common__ import _resolve_files, _relative_path, _read_text, MAX_DEPS_PER_MANIFEST

logger = logging.getLogger(__name__)


DEPENDENCY_MANIFESTS = {
    # JavaScript / TypeScript
    "package.json": "JavaScript / TypeScript (npm / Node.js)",
    "package-lock.json": "JavaScript (npm lockfile)",
    "npm-shrinkwrap.json": "JavaScript (npm lockfile)",
    "yarn.lock": "JavaScript (Yarn lockfile)",
    "pnpm-lock.yaml": "JavaScript (pnpm lockfile)",

    # Python
    "requirements.txt": "Python (pip)",
    "pyproject.toml": "Python (project / dependencies)",
    "Pipfile": "Python (Pipenv)",
    "Pipfile.lock": "Python (Pipenv lockfile)",
    "setup.py": "Python (setuptools)",
    "setup.cfg": "Python (setuptools configuration)",
    "poetry.lock": "Python (Poetry lockfile)",
    "uv.lock": "Python (uv lockfile)",
    "pdm.lock": "Python (PDM lockfile)",

    # Java
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java (Gradle)",
    "build.gradle.kts": "Java (Gradle Kotlin DSL)",
    "settings.gradle": "Java (Gradle settings)",
    "settings.gradle.kts": "Java (Gradle Kotlin settings)",
    "gradle.lockfile": "Java (Gradle dependency lockfile)",
}

_REQUIREMENTS_NAME_RE = re.compile(r"^requirements[-_.\w]*\.txt$", re.IGNORECASE)

KNOWN_FRAMEWORKS = {
    # Python: frameworks e bibliotecas
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "starlette": "Starlette",
    "sqlalchemy": "SQLAlchemy",
    "celery": "Celery",
    "pydantic": "Pydantic",
    "pytest": "pytest",
    "pandas": "pandas",
    "numpy": "NumPy",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "scikit-learn": "scikit-learn",
    "langchain": "LangChain",
    "openai": "OpenAI SDK",
    "anthropic": "Anthropic SDK",

    # JavaScript / TypeScript
    "react": "React",
    "react-dom": "React",
    "next": "Next.js",
    "vue": "Vue",
    "nuxt": "Nuxt",
    "svelte": "Svelte",
    "@angular/core": "Angular",
    "express": "Express",
    "@nestjs/core": "NestJS",
    "koa": "Koa",
    "fastify": "Fastify",
    "jest": "Jest",
    "vitest": "Vitest",
    "cypress": "Cypress",
    "playwright": "Playwright",
    "@playwright/test": "Playwright",
    "typescript": "TypeScript",
    "vite": "Vite",
    "webpack": "Webpack",
    "eslint": "ESLint",

    # Java / JVM
    "org.springframework.boot:spring-boot-starter":
        "Spring Boot",
    "org.springframework.boot:spring-boot-starter-web":
        "Spring Boot",
    "org.springframework:spring-webmvc":
        "Spring MVC",
    "org.hibernate.orm:hibernate-core":
        "Hibernate",
    "org.hibernate:hibernate-core":
        "Hibernate",
    "org.junit.jupiter:junit-jupiter":
        "JUnit 5",
    "junit:junit":
        "JUnit 4",
    "org.mockito:mockito-core":
        "Mockito",
    "io.quarkus:quarkus-core":
        "Quarkus",
    "io.micronaut:micronaut-core":
        "Micronaut",
}


def _clean_version(value: Any) -> str | None:
    """Normaliza especificações de versão; omite URLs/refs diretas (podem conter credenciais)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "://" in text or text.startswith(("git+", "git@")):
        return "(direct reference)"
    return text[:100]


def _dep(name: str, version: Any, scope: str) -> dict[str, Any]:
    return {"name": name, "version_spec": _clean_version(version), "scope": scope}


_PEP508_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*([^;#]*)")


def _parse_requirement(line: str, scope: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line or line.startswith(("#", "-")):   # comentários e opções (-r, -e, --index-url…)
        return None
    match = _PEP508_RE.match(line)
    if not match:
        return None
    rest = match.group(2).strip()
    if rest.startswith("@"):
        rest = "(direct reference)"
    return _dep(match.group(1), rest or None, scope)


def _toml_loads(text: str) -> dict[str, Any] | None:
    if tomllib is None:
        return None
    try:
        return tomllib.loads(text)
    except ValueError:
        return None


def _deps_package_json(text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(text)
    except ValueError:
        return []
    deps: list[dict[str, Any]] = []
    if not isinstance(data, dict):
        return deps
    for section, scope in (
        ("dependencies", "runtime"), ("devDependencies", "dev"),
        ("peerDependencies", "peer"), ("optionalDependencies", "optional"),
    ):
        table = data.get(section)
        if isinstance(table, dict):
            deps += [_dep(n, v if isinstance(v, str) else None, scope) for n, v in table.items()]
    return deps


def _deps_requirements(text: str) -> list[dict[str, Any]]:
    return [d for d in (_parse_requirement(l, "runtime") for l in text.splitlines()) if d]


def _toml_table_deps(table: Any, scope: str, skip: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    """Tabelas `nome = "versão"` ou `nome = {version=..., git=...}` (Poetry, Cargo, Pipfile)."""
    deps: list[dict[str, Any]] = []
    if not isinstance(table, dict):
        return deps
    for name, spec in table.items():
        if name in skip:
            continue
        if isinstance(spec, str):
            version: Any = spec
        elif isinstance(spec, dict):
            version = spec.get("version")
            if version is None and any(k in spec for k in ("git", "path", "url")):
                version = "(direct reference)"
        else:
            version = None
        deps.append(_dep(name, version, scope))
    return deps


def _deps_pyproject(text: str) -> list[dict[str, Any]]:
    data = _toml_loads(text)
    if not data:
        return []
    deps: list[dict[str, Any]] = []
    project = data.get("project") or {}
    for spec in project.get("dependencies") or []:
        if isinstance(spec, str) and (d := _parse_requirement(spec, "runtime")):
            deps.append(d)
    for group, specs in (project.get("optional-dependencies") or {}).items():
        deps += [d for s in specs if isinstance(s, str) and (d := _parse_requirement(s, f"optional:{group}"))]
    for group, specs in (data.get("dependency-groups") or {}).items():
        deps += [d for s in specs if isinstance(s, str) and (d := _parse_requirement(s, f"group:{group}"))]

    poetry = (data.get("tool") or {}).get("poetry") or {}
    deps += _toml_table_deps(poetry.get("dependencies"), "runtime", skip=("python",))
    deps += _toml_table_deps(poetry.get("dev-dependencies"), "dev", skip=("python",))
    for group, content in (poetry.get("group") or {}).items():
        if isinstance(content, dict):
            deps += _toml_table_deps(content.get("dependencies"), f"group:{group}", skip=("python",))
    return deps


def _deps_pipfile(text: str) -> list[dict[str, Any]]:
    data = _toml_loads(text) or {}
    return (_toml_table_deps(data.get("packages"), "runtime")
            + _toml_table_deps(data.get("dev-packages"), "dev"))


def _pom_tag(block: str, tag: str) -> str | None:
    match = re.search(rf"<{tag}>\s*([^<]+?)\s*</{tag}>", block)
    return match.group(1) if match else None


def _deps_pom(text: str) -> list[dict[str, Any]]:
    # Regex em vez de um parser XML: evita expansão de entidades em ficheiros não confiáveis.
    deps: list[dict[str, Any]] = []
    for block in re.findall(r"<dependency>(.*?)</dependency>", text, flags=re.DOTALL):
        group, artifact = _pom_tag(block, "groupId"), _pom_tag(block, "artifactId")
        if artifact:
            deps.append(_dep(f"{group}:{artifact}" if group else artifact,
                             _pom_tag(block, "version"), _pom_tag(block, "scope") or "compile"))
    return deps


_GRADLE_CONFIGS = {
    "implementation", "api", "compileOnly", "runtimeOnly", "testImplementation",
    "testCompileOnly", "testRuntimeOnly", "annotationProcessor", "kapt", "ksp", "classpath",
    "compile", "runtime", "testCompile", "developmentOnly", "androidTestImplementation",
    "debugImplementation", "releaseImplementation",
}
_GRADLE_DEP_RE = re.compile(
    r"""^\s*(?P<conf>[A-Za-z][A-Za-z0-9_]*)\s*\(?\s*["'](?P<group>[^"':\s]+):(?P<name>[^"':\s]+)"""
    r"""(?::(?P<version>[^"'\s]+))?["']""",
    re.MULTILINE,
)


def _deps_gradle(text: str) -> list[dict[str, Any]]:
    return [
        _dep(f"{m.group('group')}:{m.group('name')}", m.group("version"), m.group("conf"))
        for m in _GRADLE_DEP_RE.finditer(text)
        if m.group("conf") in _GRADLE_CONFIGS
    ]


def _manifest_ecosystem(path: Path) -> str | None:
    if path.name in DEPENDENCY_MANIFESTS:
        return DEPENDENCY_MANIFESTS[path.name]
    if _REQUIREMENTS_NAME_RE.match(path.name):
        return "Python (pip)"
    if path.suffix.lower() == ".txt" and path.parent.name.lower() == "requirements":
        return "Python (pip)"
    return None


def _manifest_parser(path: Path):
    name = path.name
    if name == "package.json":
        return _deps_package_json
    """ if name == "composer.json":
        return _deps_composer_json """
    if name == "pyproject.toml":
        return _deps_pyproject
    if name == "Pipfile":
        return _deps_pipfile
    """ if name == "Cargo.toml":
        return _deps_cargo """
    if name == "pom.xml":
        return _deps_pom
    if name in {"build.gradle", "build.gradle.kts"}:
        return _deps_gradle
    """ if name == "go.mod":
        return _deps_go_mod """
    """ if name == "Gemfile":
        return _deps_gemfile """
    if _manifest_ecosystem(path) == "Python (pip)":
        return _deps_requirements
    return None   # lockfiles e manifestos sem parser: apenas listados


def _normalize(name: str) -> str:
    """Minúsculas e '_' -> '-' (scikit_learn == scikit-learn). Mantém '.' e ':' das coordenadas Maven."""
    return name.strip().lower().replace("_", "-")


# prefixo normalizado -> framework (cobre starters, módulos e pacotes com scope)
_FRAMEWORK_PREFIXES = (
    ("org.springframework.boot:", "Spring Boot"),
    ("@angular/", "Angular"),
    ("@nestjs/", "NestJS"),
)


def _detect_frameworks(names: set[str]) -> list[str]:
    found: set[str] = set()
    for name in names:
        key = _normalize(name)
        if key in KNOWN_FRAMEWORKS:
            found.add(KNOWN_FRAMEWORKS[key])
        for prefix, label in _FRAMEWORK_PREFIXES:
            if key.startswith(prefix):
                found.add(label)
    return sorted(found)


def collect_frameworks_dependencies(
    repo_path: Path, files: list[Path] | None = None
) -> dict[str, Any]:
    manifests: list[dict[str, Any]] = []
    all_names: set[str] = set()
    ecosystems: Counter[str] = Counter()

    for path in _resolve_files(repo_path, files):
        ecosystem = _manifest_ecosystem(path)
        if not ecosystem:
            continue
        ecosystems[ecosystem] += 1
        entry: dict[str, Any] = {
            "file": _relative_path(repo_path, path),
            "ecosystem": ecosystem,
            "parsed": False,
            "dependencies": [],
        }
        parser = _manifest_parser(path)
        text = _read_text(path) if parser else None
        if parser and text is not None:
            deps = parser(text)
            entry["parsed"] = True
            entry["dependencies_count"] = len(deps)
            entry["dependencies"] = deps[:MAX_DEPS_PER_MANIFEST]
            entry["truncated"] = len(deps) > MAX_DEPS_PER_MANIFEST
            all_names.update(d["name"] for d in deps)
        manifests.append(entry)

    return {
        "manifest_count": len(manifests),
        "ecosystems": dict(ecosystems.most_common()),
        "unique_dependencies_count": len(all_names),
        "detected_frameworks": _detect_frameworks(all_names),
        "manifests": manifests,
        "limitations": (
            "Dependências declaradas, não necessariamente utilizadas. Versões podem ser "
            "intervalos ou variáveis (${...}). pom.xml/Gradle/Gemfile lidos por regex. "
            "'detected_frameworks' é heurístico (nomes conhecidos). pyproject/Cargo/Pipfile "
            "exigem Python 3.11+ (ou o pacote 'tomli')."
        ),
    }
