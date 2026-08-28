from usher.resolver import FieldResolver
from usher.schemas import CandidateProfile
from usher.llm import LLMClient

class MockLLMClient(LLMClient):
    def __init__(self):
        super().__init__()
        
    def is_configured(self):
        return True
        
    def resolve_field_tier2(self, field_label, profile):
        from usher.llm import Tier2Resolution
        return Tier2Resolution(resolved_value="tier2_mock_value", confidence=0.90, reasoning="mock")
        
    def resolve_field_tier3(self, field_label, profile, job_context=""):
        return "tier3_generated_text"


def make_profile(**kwargs):
    defaults = {
        "full_name": "Test Candidate",
        "email": "test@example.com",
        "phone": "+1234567890",
        "location": "Bengaluru, India"
    }
    defaults.update(kwargs)
    return CandidateProfile(**defaults)


def test_resolver_tier0():
    resolver = FieldResolver(llm_client=MockLLMClient())
    resolver.register_tier0("email", lambda p: p.email)
    
    profile = make_profile(email="test@example.com")
    res = resolver.resolve("Email", profile)
    
    assert res.resolution_tier == "tier0_selector"
    assert res.resolved_value == "test@example.com"
    assert res.confidence == 1.0

def test_resolver_tier1():
    resolver = FieldResolver(llm_client=MockLLMClient())
    resolver.register_tier1("salary", lambda p: p.salary_expectation or "")
    
    profile = make_profile(salary_expectation="100k")
    res = resolver.resolve("Expected Salary", profile)
    
    assert res.resolution_tier == "tier1_fuzzy"
    assert res.resolved_value == "100k"
    assert res.confidence == 0.95

def test_resolver_tier2():
    resolver = FieldResolver(llm_client=MockLLMClient())
    profile = make_profile()
    res = resolver.resolve("Unknown Field", profile)
    
    assert res.resolution_tier == "tier2_llm_light"
    assert res.resolved_value == "tier2_mock_value"
    assert res.confidence == 0.90

def test_resolver_tier3_free_text():
    resolver = FieldResolver(llm_client=MockLLMClient())
    profile = make_profile()
    
    res = resolver.resolve("Why do you want to join us?", profile, is_free_text=True)
    
    assert res.resolution_tier == "tier3_llm_heavy"
    assert res.resolved_value == "tier3_generated_text"
    assert res.confidence == 0.0 # Tier 3 forces 0.0 to ensure manual review
