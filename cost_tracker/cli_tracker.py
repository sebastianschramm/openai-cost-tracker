import runpy
import sys

from cost_tracker.tracker import init_tracker


def track_costs():
    """
    Initialize the OpenAI cost tracker and then run the original CLI command.
    Preserves original sys.argv while adding tracking capabilities.
    """
    init_tracker()

    if len(sys.argv) < 2:
        print("Usage: track-costs module_name [args...]")
        sys.exit(1)

    module_spec = sys.argv[1]
    sys.argv = sys.argv[1:]

    try:
        runpy.run_module(module_spec, run_name="__main__", alter_sys=True)
    except ImportError as e:
        print(
            f"Error: Could not import module '{module_spec}'. Make sure it's installed."
        )
        print(f"Original error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error running {module_spec}: {e}")
        sys.exit(1)
