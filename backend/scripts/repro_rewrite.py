import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services.chat.query_rewriter import rewrite_query
from services.ai.ai_services import AIService

# Exact history and question from benchmark fu-10
HISTORY = [
    {"role": "user", "content": "What is SparseRoute's default token budget?"},
    {"role": "assistant", "content": "The default budget B is 2,048 tokens."},
]
QUESTION = "What is the net present value of Project Lotus at the 12% discount rate?"


def main():
    call_log = []

    orig_execute = AIService._execute_with_fallback

    def tracking_execute(self, providers, prompt, *args, **kwargs):
        current_info = {"prompt": prompt, "provider": None, "raw_output": None, "error": None}
        call_log.append(current_info)

        candidate_providers = providers
        max_fallbacks = kwargs.get("max_fallbacks")
        if max_fallbacks is not None:
            candidate_providers = providers[: max(0, max_fallbacks + 1)]

        for p_name in candidate_providers:
            prov = self._get_provider(p_name)
            if not hasattr(prov, "_orig_generate"):
                prov._orig_generate = prov.generate

                def make_wrapper(name, orig_func):
                    def wrapped(p):
                        res = orig_func(p)
                        if call_log:
                            call_log[-1]["provider"] = name
                            call_log[-1]["raw_output"] = res
                        return res
                    return wrapped

                prov.generate = make_wrapper(p_name, prov._orig_generate)

        try:
            res = orig_execute(self, providers, prompt, *args, **kwargs)
            current_info["raw_output"] = res
            return res
        except Exception as e:
            current_info["error"] = str(e)
            raise

    AIService._execute_with_fallback = tracking_execute

    print(f"Running repro_rewrite for 20 iterations...")
    print(f"Target question: {QUESTION!r}")
    print("=" * 80)

    for i in range(1, 21):
        result = rewrite_query(HISTORY, QUESTION)
        info = call_log[-1] if call_log else {}
        provider = info.get("provider", "Unknown / None")
        prompt_sent = info.get("prompt", "None")
        raw_output = info.get("raw_output", "None")

        print(f"--- Call {i}/20 ---")
        print(f"Provider used: {provider}")
        print(f"Exact prompt sent:\n{prompt_sent}")
        print(f"Raw output:\n{raw_output}")
        print(f"Rewrite output:\n{result}")
        print("-" * 80)


if __name__ == "__main__":
    main()
