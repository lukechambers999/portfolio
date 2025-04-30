# Welcome to my football betting and analytics portfolio

This repository showcases a selection of projects that I have been working on as part of my own sports betting operation, as well as other areas of sports betting and analytics that interest me. Each project below includes a quick intro and everything you need to run the code.

# Long Term Model

This project creates predictions for every match for the rest of the season for any of the top 5 European Leagues, based on optimised goal, xG and betting line ratings.
These predictions are then used to create a league table with predicted number of points, goals scored and goals conceded at the end of the season.
It also contains predictions for each teams likelihood to finish 1st, Top 4, Top 6 and Bottom 3, derived from running Monte Carlo simulations on the rest of the seasons fixtures.

# Corner Game State Analysis

This project looks at the effect that game state has on corner performances and proposes a way of .....

## Dependencies

- See setup section below to install the required pip packages for this project

## Setup

```
# Set up venv

# Install Dependencies

# launch jupyter notebook

```

From there you can navigate to the project folder and open LT_model.ipynb.

## Data

The following data files are used in this project:
- `data/'League'.csv`: Five individual files containing historical betting odds for top 5 leagues.
- `data/goallines.csv`: Contains a lookup table to convert betting lines into goal expectancies for each match.
- `data/supconversion.csv`: Contains a lookup table to convert betting lines into goal expectancies for each match.
-  data/mins_conv.csv: Contains a lookup table to convert goal expectancies into expected winning, drawing and losing minutes for each match.
-  data/corner_gamestate.csv.csv: Contains event level data for a range of leagues for game state analysis

These files are located in the `data/` folder.

In addition to these files the LT_model script scrapes historical and future fixture information using the Understat API

## Contact
For questions or feedback, feel free to reach out:
- luke.chambers999@gmail.com

