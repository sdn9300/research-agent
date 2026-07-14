PYTHON ?= python

.PHONY: validate-fact-set gate1 phase1 validate-phase1 phase2 validate-phase2 eval phase3 validate-phase3
 
validate-fact-set:
	$(PYTHON) eval/validate_fact_set.py
 
gate1: validate-fact-set
 
phase1:
	$(PYTHON) scripts/validate_phase1.py
 
validate-phase1: phase1
 
phase2:
	$(PYTHON) scripts/validate_phase2.py
 
validate-phase2: phase2

eval:
	$(PYTHON) eval/run_eval.py

phase3: eval
	$(PYTHON) scripts/verify_logger.py

validate-phase3: phase3

