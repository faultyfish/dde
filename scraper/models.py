"""
scraper/models.py
Job dataclass + category/level/stack classification logic.
"""
import re
import hashlib
from dataclasses import dataclass, field
from typing import Optional

# ── Category keywords ────────────────────────────────────────────────────────
CATEGORY_RULES = {
    "MLOps":  ["mlops", "ml engineer", "machine learning engineer", "mlflow",
                "kubeflow", "data platform", "ai infrastructure"],
    "SRE":    ["site reliability", "sre", "reliability engineer"],
    "Cloud":  ["cloud engineer", "cloud infrastructure", "cloud architect",
                "aws engineer", "azure engineer", "gcp engineer",
                "solutions architect", "finops", "cloud platform"],
    "DevOps": ["devops", "platform engineer", "ci/cd", "infrastructure engineer",
                "build engineer", "release engineer"],
}

LEVEL_RULES = {
    "Lead":    ["lead", "principal", "staff", "head of", "vp "],
    "Senior":  ["senior", "sr.", "sr "],
    "Junior":  ["junior", "jr.", "jr ", "associate", "entry level", "entry-level", "graduate"],
    "Graduate":["graduate", "grad programme", "grad scheme", "intern"],
}

STACK_KEYWORDS = [
    "kubernetes", "k8s", "docker", "terraform", "ansible", "helm",
    "aws", "azure", "gcp", "google cloud",
    "jenkins", "github actions", "gitlab ci", "circleci", "argo",
    "prometheus", "grafana", "datadog", "splunk", "new relic",
    "python", "go", "bash", "powershell", "ruby",
    "linux", "networking", "istio", "vault", "consul",
    "mlflow", "kubeflow", "airflow", "spark",
    "postgres", "redis", "kafka", "rabbitmq",
    "keda", "opentelemetry", "trivy",
]

VISA_KEYWORDS = ["visa sponsor", "stamp 4", "critical skills", "work permit",
                  "eligible to work", "sponsorship available"]

SALARY_PATTERN = re.compile(
    r"(?:€|eur|EUR)?\s*(\d[\d,]*)\s*(?:k|K)?(?:\s*[-–to]+\s*(?:€|eur|EUR)?\s*(\d[\d,]*)\s*(?:k|K)?)?",
    re.IGNORECASE
)


def classify_category(title: str, description: str) -> str:
    text = (title + " " + description).lower()
    for cat, keywords in CATEGORY_RULES.items():
        if any(kw in text for kw in keywords):
            return cat
    return "DevOps"  # default


def classify_level(title: str, description: str) -> str:
    text = (title + " " + description).lower()
    for level, keywords in LEVEL_RULES.items():
        if any(kw in text for kw in keywords):
            return level
    return "Mid"  # default


def extract_stack(description: str) -> list[str]:
    text = description.lower()
    found = []
    for kw in STACK_KEYWORDS:
        if kw in text and kw not in found:
            found.append(kw.title().replace("Aws", "AWS").replace("Gcp", "GCP")
                         .replace("Ci/Cd", "CI/CD").replace("K8S", "K8s")
                         .replace("Keda", "KEDA"))
    return found[:12]  # cap at 12 tags


def parse_salary(salary_raw: str) -> tuple[Optional[int], Optional[int]]:
    if not salary_raw:
        return None, None
    matches = SALARY_PATTERN.findall(salary_raw)
    if not matches:
        return None, None
    try:
        low_str, high_str = matches[0]
        low_str = low_str.replace(",", "")
        high_str = high_str.replace(",", "") if high_str else low_str
        low = int(low_str)
        high = int(high_str)
        # Detect if thousands need multiplying (e.g. "80k")
        if "k" in salary_raw.lower():
            if low < 1000:
                low *= 1000
            if high < 1000:
                high *= 1000
        return low, high
    except Exception:
        return None, None


def check_visa_sponsor(description: str) -> bool:
    text = description.lower()
    return any(kw in text for kw in VISA_KEYWORDS)


def make_external_id(source: str, url: str) -> str:
    """Stable hash of URL as external_id when source doesn't provide one."""
    return hashlib.sha256(f"{source}:{url}".encode()).hexdigest()[:16]


@dataclass
class Job:
    external_id: str
    source: str           # 'indeed' | 'linkedin'
    title: str
    company: str
    location: str
    url: str
    description: str = ""
    remote_type: str = "On-site"
    job_type: str = "Full-time"
    salary_raw: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    category: str = ""
    level: str = ""
    stack: list = field(default_factory=list)
    visa_sponsor: bool = False

    def enrich(self):
        """Run classification after scraping."""
        self.category = classify_category(self.title, self.description)
        self.level = classify_level(self.title, self.description)
        self.stack = extract_stack(self.description)
        self.salary_min, self.salary_max = parse_salary(self.salary_raw)
        self.visa_sponsor = check_visa_sponsor(self.description)
        return self

    def to_db_dict(self) -> dict:
        return {
            "external_id": self.external_id,
            "source": self.source,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "remote_type": self.remote_type,
            "job_type": self.job_type,
            "salary_raw": self.salary_raw,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "description": self.description,
            "url": self.url,
            "category": self.category,
            "level": self.level,
            "stack": self.stack,
            "visa_sponsor": self.visa_sponsor,
        }
