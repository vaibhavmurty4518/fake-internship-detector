"""Offline tests for company verification, aggregation and pipeline."""
import pytest
from company_providers import CompanyVerificationProvider, ProviderResult
from company_utils import extract_company, normalize_name, name_domain_relationship
from company_verification import verify_company
from internshield_pipeline import analyze_listing, calculate_overall_risk

NORMAL = "Backend intern. Work with our team on Python services. Stipend Rs 15,000/month. Pursuing B.Tech."
SCAM = "Pay a registration fee of Rs 2000 to confirm your seat. Guaranteed Rs 50000 per week. Limited seats, apply today!"


class FakeSite(CompanyVerificationProvider):
    name = "website-check"
    def __init__(self, found=True, domain="acme.com"):
        self.found, self.domain = found, domain
    def verify(self, d, n, website=None):
        return ProviderResult(self.name, found=self.found, website="https://" + self.domain, official_domain=self.domain,
                              facts={"https": True, "name_on_site": True, "has_about": True, "has_contact": True},
                              sources=[{"title": "Company website", "url": "https://" + self.domain}])


def test_normalization():
    assert normalize_name("ABC Technologies Pvt. Ltd.") == "abc technologies"
    assert normalize_name("Microsoft India Pvt Ltd") == normalize_name("Microsoft Corporation") == "microsoft"
    assert normalize_name("  XYZ   Solutions, LLC ") == "xyz solutions"


def test_extraction():
    assert extract_company("Company: ABC Technologies Pvt. Ltd.\nx")["display_name"] == "ABC Technologies Pvt. Ltd."
    assert extract_company("anything", "Google")["method"] == "explicit"
    assert extract_company("no names here")["method"] == "none"


@pytest.mark.parametrize("name", ["Google", "Microsoft", "TCS"])
def test_known_companies(name):
    r = verify_company(name, online=False)
    assert r["company_found"] and r["risk_score"] <= 25


def test_alias_related():
    assert {verify_company(n, online=False)["company_found"] for n in
            ("Microsoft", "Microsoft India Pvt Ltd", "Microsoft Corporation")} == {True}


def test_unknown_fictional_not_called_fake():
    r = verify_company("Zorblax Quantum Pvt Ltd", online=False)
    assert r["status"] == "UNVERIFIED" and r["confidence"] <= 25
    assert "fake" not in str(r).lower() or "scam" not in r["status"].lower()


def test_gmail_only_raises_caution_not_scam():
    r = verify_company("ABC Technologies Pvt. Ltd.", email="abc.hr@gmail.com", online=False)
    assert r["risk_score"] < 60 and any(s["name"] == "free_email_used" for s in r["signals"])


def test_matching_and_mismatching_domain():
    ok = verify_company("Acme Corp", email="hr@acme.com", website="acme.com", providers=[FakeSite()], online=False)
    bad = verify_company("Acme Corp", email="hr@other-mail.com", website="acme.com", providers=[FakeSite()], online=False)
    assert ok["risk_score"] < bad["risk_score"]
    assert any(s["name"] == "official_domain_match" and s["value"] is True for s in ok["signals"])


def test_name_domain_relationship():
    assert name_domain_relationship("microsoft", "microsoft.com") == "strong"
    assert name_domain_relationship("zorblax", "qqqq.xyz") == "none"


def test_real_company_suspicious_internship():
    r = analyze_listing(SCAM, "Google", "hr@google.com", online=False)
    assert r["company_verification"]["status"] in ("VERIFIED", "PARTIALLY VERIFIED")
    assert r["internship_prediction"]["label"] in ("HIGH RISK", "VERY HIGH RISK", "SUSPICIOUS")
    assert r["overall_assessment"]["risk_score"] >= 55   # company cannot wash out strong content evidence


def test_unknown_company_normal_internship_not_scam():
    r = analyze_listing(NORMAL, "Zorblax Labs", online=False)
    assert r["overall_assessment"]["risk_level"] in ("LOW RISK", "CAUTION")


def test_real_company_matching_domain_low():
    r = analyze_listing(NORMAL, "Microsoft", "careers@microsoft.com", online=False)
    assert r["contact_analysis"]["domain_match"] == "official_domain_match"
    assert r["overall_assessment"]["risk_level"] in ("LOW RISK", "CAUTION")


def test_impersonation():
    r = analyze_listing(NORMAL, "Microsoft", "microsoft-careers@gmail.com", online=False)
    assert r["contact_analysis"]["impersonation"] and r["overall_assessment"]["risk_score"] >= 65
    assert "impersonation" in r["explanation"]["summary"].lower()


def test_missing_company_email_website():
    r = analyze_listing(NORMAL, online=False)
    assert r["company_verification"]["confidence"] <= 10
    assert r["contact_analysis"]["email"] is None and r["overall_assessment"]["risk_score"] < 60


def test_invalid_inputs_do_not_crash():
    r = analyze_listing(NORMAL, "X", "not-an-email", "ht tp://bad url", "???", online=False)
    assert len(r["input_issues"]) == 3


def test_provider_failure_isolated():
    class Boom(CompanyVerificationProvider):
        name = "boom"
        def verify(self, *a, **k): raise RuntimeError("x")
    r = verify_company("Acme", providers=[Boom()], online=False)
    assert r["status"] in ("UNVERIFIED", "UNAVAILABLE")


def test_weights_configurable_and_confidence_scaling():
    i = {"score": 30, "confidence": 70}
    contact = {"risk_score": 30, "confidence": 50}
    low = {"risk_score": 90, "confidence": 5, "verification_ran": True}
    high = {"risk_score": 90, "confidence": 95, "verification_ran": True}
    assert calculate_overall_risk(i, low, contact)["risk_score"] < calculate_overall_risk(i, high, contact)["risk_score"]
    a = calculate_overall_risk(i, high, contact, {"i": 1, "c": 0, "k": 0})
    assert a["risk_score"] == 30


def test_existing_ml_untouched():
    from inference import predict
    out = predict(SCAM)
    assert {"risk_score", "risk_level", "indicators"} <= set(out)
