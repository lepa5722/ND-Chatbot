
import os
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# LLM CONFIGURATION
# ============================================================

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")
# Supported providers: "echo", "local", "openai"

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "phi-4-IQ2_XS.gguf"
)

LLM_API_KEY = os.getenv("LLM_API_KEY", "")

LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "http://127.0.0.1:8080/v1"
)

LLM_TEMPERATURE = float(
    os.getenv("LLM_TEMPERATURE", "0")
)

# Memory-conscious inference limits
LLM_MAX_TOKENS = int(
    os.getenv("LLM_MAX_TOKENS", "256")
)

LLM_CONTEXT_SIZE = int(
    os.getenv("LLM_CONTEXT_SIZE", "512")
)

LLM_TIMEOUT = float(
    os.getenv("LLM_TIMEOUT", "60")
)


# ============================================================
# ADAPTATION PARAMETERS
# Frozen specification v1.0
# ============================================================

EPSILON = float(
    os.getenv("EPSILON", "0.1")
)

RANDOM_SEED = int(
    os.getenv("RANDOM_SEED", "42")
)

FIXATION_SHARE = float(
    os.getenv("FIXATION_SHARE", "0.5")
)

FIXATION_MIN_THOUGHTS = int(
    os.getenv("FIXATION_MIN_THOUGHTS", "3")
)

SHALLOW_BELOW = float(
    os.getenv("SHALLOW_BELOW", "2.0")
)

DECAY_RATE = float(
    os.getenv("DECAY_RATE", "0.5")
)

DECAY_FLOOR = float(
    os.getenv("DECAY_FLOOR", "0.25")
)

SIGNAL_CUTOFF = float(
    os.getenv("SIGNAL_CUTOFF", "0.7")
)

SHORT_TOKENS = int(
    os.getenv("SHORT_TOKENS", "15")
)

DISMISSAL_TRIGGER = int(
    os.getenv("DISMISSAL_TRIGGER", "2")
)


# ============================================================
# POLICY CONFIGURATION
# ============================================================

POLICY_VERSION = os.getenv(
    "POLICY_VERSION",
    "policies-v1.0"
)


# ============================================================
# DATA CONFIGURATION
# ============================================================

DATA_DIR = os.getenv(
    "DATA_DIR",
    "data"
)