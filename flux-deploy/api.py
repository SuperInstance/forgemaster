"""FLUX Constraint API — lightweight Flask server."""

from flask import Flask, request, jsonify

app = Flask(__name__)


def check_constraints(value, constraints, mode="and"):
    """Evaluate value against a list of {lo, hi} constraint dicts."""
    results = []
    for c in constraints:
        lo = c.get("lo", float("-inf"))
        hi = c.get("hi", float("inf"))
        passed = lo <= value <= hi
        results.append({"lo": lo, "hi": hi, "passed": passed})

    if mode == "or":
        overall = any(r["passed"] for r in results)
    else:
        overall = all(r["passed"] for r in results)

    return {"value": value, "results": results, "passed": overall}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "flux-api"})


@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(force=True)
    value = data["value"]
    constraints = data["constraints"]
    mode = data.get("mode", "and")
    result = check_constraints(value, constraints, mode)
    return jsonify(result)


@app.route("/batch", methods=["POST"])
def batch():
    data = request.get_json(force=True)
    values = data["values"]
    constraints = data["constraints"]
    mode = data.get("mode", "and")
    results = [check_constraints(v, constraints, mode) for v in values]
    all_passed = all(r["passed"] for r in results)
    return jsonify({"batch": results, "all_passed": all_passed})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
