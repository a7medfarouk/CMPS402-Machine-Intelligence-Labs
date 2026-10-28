"""Run optional adapter checks separately: uv run --locked --extra gym -m optional_gym.checks."""

import argparse
import importlib.util
from pathlib import Path
import traceback
import unittest

from campus.actions import detail, save_json
from campus.feedback import LABELS, describe_error, table
from campus.loading import load_bundle
from campus.maps import MapSpec
from campus.terminal import notice, progress, say, show_table, verdict


ROOT = Path(__file__).resolve().parents[1]
TITLES = {
    "test_reset_observation_and_action_order": "Reset, observation spaces, and action order",
    "test_weighted_route_matches_model_and_terminates": "Weighted movement and goal completion",
    "test_illegal_move_stays_put_and_counts_toward_limit": "Illegal moves and the step limit",
    "test_goal_wins_over_time_limit_on_same_step": "Goal completion takes precedence over the limit",
    "test_pickup_unlocks_door_and_destination_requires_pickup": "Pickup, doors, and an early destination visit",
    "test_reset_clears_episode_and_render_returns_text": "Reset clears the episode; rendering returns text",
    "test_invalid_action_and_step_before_reset": "Invalid actions and episode order",
    "test_gymnasium_api": "Gymnasium API compatibility",
}


def suite(environment_class, model_class):
    class AdapterTests(unittest.TestCase):
        def environment(self, rows=("SwG", "..."), limit=100):
            return environment_class(MapSpec(rows), max_steps=limit, render_mode="ansi", model_class=model_class)

        def test_reset_observation_and_action_order(self):
            environment = self.environment()
            observation, info = environment.reset(seed=7)
            self.assertTrue(environment.observation_space.contains(observation))
            self.assertEqual(observation, {"row": 0, "column": 0, "has_key": 0})
            self.assertEqual(info["action_mask"], [0, 1, 1, 0])
            self.assertEqual(info["steps"], 0)

        def test_weighted_route_matches_model_and_terminates(self):
            environment = self.environment()
            environment.reset()
            observation, reward, terminated, truncated, info = environment.step(1)
            self.assertEqual(reward, -5)
            self.assertFalse(terminated or truncated)
            self.assertEqual(observation["column"], 1)
            observation, reward, terminated, truncated, info = environment.step(1)
            self.assertEqual(reward, -1)
            self.assertTrue(terminated)
            self.assertFalse(truncated)
            self.assertEqual(info["action_mask"], [0, 0, 0, 0])
            with self.assertRaises(RuntimeError):
                environment.step(1)

        def test_illegal_move_stays_put_and_counts_toward_limit(self):
            environment = self.environment(limit=1)
            before, unused = environment.reset()
            after, reward, terminated, truncated, info = environment.step(0)
            self.assertEqual(after, before)
            self.assertEqual(reward, -1)
            self.assertFalse(terminated)
            self.assertTrue(truncated)
            self.assertEqual(info["steps"], 1)

        def test_goal_wins_over_time_limit_on_same_step(self):
            environment = self.environment(("SG",), limit=1)
            environment.reset()
            observation, reward, terminated, truncated, info = environment.step(1)
            self.assertEqual(reward, -1)
            self.assertTrue(terminated)
            self.assertFalse(truncated)

        def test_pickup_unlocks_door_and_destination_requires_pickup(self):
            environment = self.environment(("SKDG",))
            environment.reset()
            observation, reward, terminated, truncated, info = environment.step(1)
            self.assertEqual(observation["has_key"], 1)
            self.assertEqual(info["action_mask"], [0, 1, 0, 1])
            environment.step(1)
            self.assertTrue(environment.step(1)[2])
            early = self.environment(("SG.K",))
            early.reset()
            self.assertFalse(early.step(1)[2])

        def test_reset_clears_episode_and_render_returns_text(self):
            environment = self.environment()
            first, unused = environment.reset(seed=9)
            environment.step(1)
            again, info = environment.reset(seed=9)
            self.assertEqual(first, again)
            self.assertEqual(info["steps"], 0)
            self.assertIn("@", environment.render())
            environment.close()

        def test_invalid_action_and_step_before_reset(self):
            environment = self.environment()
            with self.assertRaises(RuntimeError):
                environment.step(1)
            environment.reset()
            with self.assertRaises(ValueError):
                environment.step(4)

        def test_gymnasium_api(self):
            from gymnasium.utils.env_checker import check_env
            environment = self.environment()
            check_env(environment, skip_render_check=True)
            environment.close()

    return unittest.TestSuite(AdapterTests(name) for name in TITLES)


class CheckResults(unittest.TestResult):
    def __init__(self, on_result=None):
        super().__init__()
        self.checks = []
        self.on_result = on_result

    def record(self, test, error=None):
        name = test._testMethodName
        item = {"number": list(TITLES).index(name) + 1 if name in TITLES else len(self.checks) + 1, "check": TITLES.get(name, name.removeprefix("test_").replace("_", " ")), "passed": error is None, "status": "ok"}
        if error is not None:
            item.update(describe_error(error[1]))
            if not item.get("location"):
                frames = traceback.extract_tb(error[2])
                useful_frames = [frame for frame in frames if "/unittest/" not in frame.filename.replace("\\", "/")]
                adapter_frames = [frame for frame in useful_frames if Path(frame.filename).resolve() != Path(__file__).resolve()]
                if adapter_frames or useful_frames:
                    frame = (adapter_frames or useful_frames)[-1]
                    item["location"] = f"{frame.filename}:{frame.lineno}"
            if item["status"] == "not_implemented":
                item["hint"] = "Complete reset and step in optional_gym/environment.py, and any unfinished model methods used by the adapter."
            elif item["status"] == "wrong_answer":
                item["hint"] = "Compare your adapter with Section 9 of the assignment guide; re-run this optional check with --case NUMBER --details."
        self.checks.append(item)
        if self.on_result is not None:
            self.on_result(item)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test)

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.record(test, error)

    def addError(self, test, error):
        super().addError(test, error)
        self.record(test, error)


def run_checks(tests, on_result=None):
    result = CheckResults(on_result)
    tests.run(result)
    return {"checks": result.checks, "passed": sum(item["passed"] for item in result.checks), "total": result.testsRun, "scope": "Optional Gymnasium diagnostics only; these do not change the assignment mark or required public-check results."}


def present_results(report, details=False):
    show_table(["#", "Optional check", "Result"], [(item["number"], item["check"], verdict(item["status"])) for item in report["checks"]], "Optional Gymnasium checks")
    say(f"Passed {report['passed']}/{report['total']}. Optional checks do not affect the assignment mark.")
    failures = [item for item in report["checks"] if not item["passed"]]
    for item in failures if details else failures[:3]:
        notice(detail(item), f"Optional check {item['number']}: {item['check']}", "yellow")
    if len(failures) > 3 and not details:
        say("More failures: re-run with --details, or --case NUMBER --details.", "dim")
    say("Full diagnostics: output/optional-gym-checks.txt", "dim")


def save_report(report):
    save_json(ROOT / "output/optional-gym-checks.json", report)
    text = table(["#", "Optional check", "Result"], [(item["number"], item["check"], LABELS[item["status"]]) for item in report["checks"]])
    text += f"\n\nPassed {report['passed']}/{report['total']}. Optional and ungraded; separate from required public checks."
    for item in report["checks"]:
        if not item["passed"]:
            text += f"\n\n[{item['number']}] {item['check']}\n" + detail(item)
    (ROOT / "output/optional-gym-checks.txt").write_text(text + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, default=ROOT / "submission")
    parser.add_argument("--adapter", type=Path, default=ROOT / "optional_gym/environment.py")
    parser.add_argument("--case", help="An optional-check number (1-8) or part of its name")
    parser.add_argument("--details", action="store_true", help="Show all failure details, not just the first three")
    arguments = parser.parse_args()
    if importlib.util.find_spec("gymnasium") is None:
        notice("Run: uv sync --locked --extra gym\nThis dependency is only needed for the ungraded extension.", "Gymnasium is not installed", "yellow")
        return 2
    try:
        specification = importlib.util.spec_from_file_location("optional_adapter", arguments.adapter.resolve())
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        bundle = load_bundle(arguments.submission)
        tests = list(suite(module.CampusCourierEnv, bundle.Model))
        if arguments.case is not None:
            value = arguments.case.casefold()
            tests = [test for index, test in enumerate(tests, 1) if (str(index) == value if value.isdigit() else value in TITLES[test._testMethodName].casefold())]
            if not tests:
                raise ValueError("No matching optional check. Use a number from 1 to 8 or part of its name.")
        notice("Optional and ungraded. These results are separate from the required public checks.", "Gymnasium extension")
        with progress(len(tests), "Checking your optional adapter") as advance:
            report = run_checks(unittest.TestSuite(tests), on_result=lambda item: advance(item["check"]))
        save_report(report)
        present_results(report, arguments.details)
        return 0 if report["passed"] == report["total"] else 1
    except KeyboardInterrupt:
        say("Optional checks cancelled.", "yellow")
        return 130
    except Exception as error:
        notice(detail(describe_error(error)), "Could not run optional checks", "red")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
