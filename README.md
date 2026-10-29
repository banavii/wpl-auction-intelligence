🚀 **Live Demo:** https://wpl-auction-intelligence.streamlit.app/

💻 **Source Code:** https://github.com/banavii/wpl-auction-intelligence


# 🏏 WPL Auction Intelligence

A data-driven cricket analytics application designed to support Women's Premier League (WPL) auction preparation through player performance analysis, role-based filtering, player comparisons, and Impact Index rankings.

## 📌 Project Overview

WPL Auction Intelligence helps users explore player statistics, shortlist potential auction targets, compare performances, and identify promising all-rounders using a custom performance metric.

The project combines Python-based data processing with an interactive Streamlit dashboard to demonstrate how cricket statistics can be transformed into actionable insights for player scouting and auction analysis.


## 📊 Dataset Transparency

The application includes a sample dataset for demonstration and testing.

- **2024:** Match data collected from individual scorecards for the 2024–25 Senior Women's T20 Trophy.
- **2025:** Synthetic records generated to support application development and demonstrate the analytics workflow.
- **Data processing:** Player records are organized into a structured dataset for filtering, comparison, and performance analysis.

**Important:** 2024 records and Synthetic 2025 records are not verified historical player performances. The Impact Index and player rankings based on these records are demonstrations of the application's calculations, not validated assessments of actual player performance.

For production use, the synthetic records should be replaced with verified match-level data, with appropriate checks for missing values, duplicate records, and player identity.

## ✨ Key Features

- **Player Explorer:** Explore player records and filter players by role.
- **Role-Specific Statistics:** View relevant batting and bowling performance metrics.
- **Player Shortlisting:** Browse unique player records and open detailed player profiles.
- **Player Profiles:** Inspect available season-wise batting and bowling performances.
- **Player Comparison:** Compare players using role-appropriate performance statistics.
- **All-Rounder Leaderboard:** Rank all-rounders by their calculated Impact Index.
- **Dataset Validation:** Inspect missing values, duplicate player names, column types, and data availability.
- **Flexible CSV Input:** Upload a CSV file containing player and performance information.

## 📊 All-Rounder Impact Index

The application calculates a custom Impact Index to rank all-rounders when the required statistics are available.

**Formula:**

Impact Index = (Runs × Strike Rate / 100) + (Wickets × 20) − (Economy × 5)

The calculation combines batting output, strike rate, wicket-taking contribution, and bowling economy.

**Important:** This is a custom project metric, not an official WPL rating or a validated prediction of future player performance.

## 🗂️ Data Collection and Preparation

Collecting historical domestic women's cricket data was a significant part of this project.

- **2024–25 Senior Women's T20 Trophy:** Collected scorecard data across 39 matches using Python-assisted workflows and Gemini for scorecard extraction and matching players against the auction list.
- **Additional 2025 data:** Generated synthetic records to support application development because the required historical data was not consistently accessible in a consolidated format.
- **Data processing:** Organized player records into a structured dataset for exploration and analysis.

Synthetic records are demonstration data and should not be interpreted as verified historical player performances. Real-world scouting decisions require validated match records.

## 🛠️ Tech Stack

- **Language:** Python
- **Data Processing:** Pandas
- **Dashboard:** Streamlit
- **AI-Assisted Extraction:** Google Gemini
- **Version Control:** Git and GitHub

## 📁 Project Structure

```text
wpl-auction-intelligence/
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/banavii/wpl-auction-intelligence.git
cd wpl-auction-intelligence
```

### 2. Create a virtual environment (optional)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 4. Run the application

```bash
streamlit run app.py
```

Open the local URL displayed in your terminal to access the dashboard.

## 📂 Input Data

The application expects a CSV file containing player names and any available player attributes or performance statistics.

Depending on the available columns, the application can identify player roles, batting statistics, bowling statistics, season information, and auction-related fields.

Available features depend on the columns present in the uploaded dataset.

## 🚀 Future Enhancements

- Integrate additional verified historical domestic cricket records.
- Automate repeatable scorecard ingestion and data validation.
- Add squad-gap analysis based on team composition and player roles.
- Develop budget-aware auction recommendations.
- Evaluate player performance prediction models using verified historical data.
- Deploy the application for interactive online access.

## 🎯 Project Objective

The objective is to demonstrate how data engineering, cricket performance analytics, and interactive visualization can support more structured player scouting and auction preparation.

## 👤 Author

**Banavi**

[GitHub Repository](https://github.com/banavii/wpl-auction-intelligence)

---

*This project is intended for educational and analytical demonstration. Player rankings and auction insights depend on data quality, coverage, and the assumptions used in the scoring methodology.*