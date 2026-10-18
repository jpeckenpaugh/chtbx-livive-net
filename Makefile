REF ?= ref.wav
OUT ?= out/voice.wav
PYTHON ?= .venv/bin/python

# Note: "Artificial" is the correct spelling (the original said "Artifical").
PHRASE ?= Artificial Intelligence & Machine Learning

.PHONY: setup record say preview clean

setup: ## Create venv and install dependencies
	./install.sh

record: ## Record a reference clip into $(REF)
	./record_ref.sh $(REF)

say: ## Synthesize $(PHRASE) in the cloned voice
	$(PYTHON) gen.py --ref $(REF) --text "$(PHRASE)" --out $(OUT)

preview: ## Play the last output
	afplay $(OUT)

clean: ## Remove generated audio
	rm -rf out $(REF)
