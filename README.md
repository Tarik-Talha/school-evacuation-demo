# School Evacuation Scenario Explorer

A Python/Streamlit project that explores student movement through an illustrative school model. It combines capacity-constrained simulation, plan comparisons, a browser-based 3D player, and Blender/OpenUSD exports.

Developed by Tarık. This repository is a portable copy of the existing school pilot; the original local installation is preserved.

## Run locally

Python 3.12 is the tested version. Create an isolated environment and install the pinned dependencies:

```sh
python -m venv .venv
```

Activate it with `.venv\Scripts\activate` on Windows or `source .venv/bin/activate` on macOS/Linux. Then run:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

No Blender installation is needed for the interactive browser demo. Blender is only needed to create or inspect a `.blend` scene from the exported data. `launch.py` and `start_school_pilot.vbs` are optional Windows launchers; the Streamlit command above works across platforms.

## What you can try

- Classroom, lunch, laboratory, and reproducible break-time starting conditions.
- Pairs/trios distributed across rooms, common areas, and the yard, without adding or losing students.
- Route closures, capacity assumptions, movement behavior, and model comparisons.
- Bounded plan search with separate search and control runs.
- Play, pause, scrub, reset, change camera, and inspect a single floor or the complete 3D model.
- Repeated trials, drill comparisons, and user-entered measurements.
- Download the model run as JSON, or the same run as Blender/OpenUSD data.

All 11 original source images are bundled with relative paths and checked against their recorded hashes. Oda/measurement edits belong to the current browser session; refreshing or opening a separate session starts with the defaults. Download reports you want to keep.

## Scope of the model

The pilot accounts for 111 anonymous model students. Teachers, staff, and visitors are outside its population scope. Room mapping, physical dimensions, and movement assumptions are not independently calibrated. Results are model outputs, not verified evacuation times, structural safety assessments, or approved emergency instructions. The response-service times are citywide historical references rather than school-specific arrival predictions.

See `README_TR.md` and the version guides for the original local pilot's modeling history. Their older workstation paths and historic test counts describe that earlier installation, not this portable release.

## Verify

```sh
python -m unittest discover -s . -p "test_*.py" -v
```

The suite checks population conservation, capacity limits, invalid inputs, blocked routes, scene/export identities, plan-search behavior, the UI, portable image assets, and independent browser-session edits. Release checks also cover multiple break-time seeds, including a regression for placement 197.

## Deployment

Run the Streamlit entry point `app.py` with Python 3.12 and `requirements.txt`. The portfolio can link to the resulting demo. Static portfolio hosting alone does not run this Python application.

## Portable-release changes

- Bundled source plans; removed reliance on the old workstation directory layout.
- Isolated interactive layout, measurement, and report edits between visitors.
- Fixed break-time placement when a selected patch cannot contain the group: another permitted space on the same floor is tried.
- Updated the new-placement button to change its value through a widget callback.
- Added release regression tests and GitHub Actions configuration.
