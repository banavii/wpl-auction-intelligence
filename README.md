# WPL Auction Intelligence

A Streamlit scouting workspace that uses the CSV uploaded by the team. It does not create or supplement player statistics.

## Run on macOS

Activate your existing Conda environment, then install the dependencies if needed:

```bash
conda install -c conda-forge streamlit pandas
streamlit run app.py
```

## Workflow

1. Upload a CSV containing a player-name column (e.g. `Player_Name`).
2. Open **Player scouting** and choose nationality, role, and role-specific categories.
3. Use **Classify players** to enter confirmed nationality, batting position, bowling type, and bowling style when these columns are absent from the uploaded file.
4. Use **Compare players** and **Dataset & exports** to compare candidates and download shortlists/exports.

## Data behavior

- The app uses only the uploaded CSV as its performance source.
- Multiple season rows are consolidated into one player row in the scouting pool, while season-level records remain available in player profiles.
- The app never infers nationality or bowling/batting subcategories from names. Missing attributes stay `Unclassified` until the team enters them.
- Team-entered classifications are session-only; download the classification CSV to preserve them.
