# Hypothesis handover-test adoption

## Decision

- Tool: Hypothesis 6.156.4, MPL-2.0.
- Existing owner: the standard-library coordination state helper and `unittest` suite.
- Outcome: test-only sidecar.
- Runtime promotion: forbidden. The plugin, SessionStart hook, Doctor, and Mission Control do not import Hypothesis.
- Custom behavior: keep the existing helper and deterministic tests; add generated action sequences around the same public state contract.

## Trial evidence

An isolated trial ran 200 generated recovery programs with up to 20 actions each. The valid single-Coordinator model passed. A seeded defect that allowed a superseded Coordinator to become accepting again was caught and reduced to a failing sequence.

The repository adoption exercises the real inbox helper across generated sequences of record creation, acknowledgement, record mutation, Coordinator replacement, coordination-epoch replacement, and repeated acknowledgement.

## Boundaries and rollback

- The dependency is installed only by `.github/workflows/property-tests.yml` or explicitly from `requirements-property-tests.txt`.
- The normal dependency-free test command remains usable and reports the property module as skipped when Hypothesis is absent.
- Hypothesis may create only temporary test data. It never reads live project coordination state or calls native task tools.
- Rollback is removal of the dedicated workflow, requirement file, property test, and this record; no runtime or project-state migration is needed.

## Acceptance checks

```shell
python -m pip install --requirement requirements-property-tests.txt
python -m unittest discover -s tests -p "test_handover_properties.py" -v
python -m unittest discover -s tests -p "test_*.py" -v
```
