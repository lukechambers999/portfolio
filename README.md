## Sports Betting & Analytisc Portfolio

This repository showcases a selection of projects that I have been working on as part of my own sports betting operation, as well as other areas of sports betting and analytics that interest me. Below is a quick intro to each project and instructions on how run and set up the analysis. The Notebooks are saved with outputs visible in the repository if you would prefer an overview.

## Long Term Model

This project creates predictions for every match for the rest of the season for any of the top 5 European Leagues, based on optimised goal, xG and betting line ratings.
These predictions are then used to create a league table with predicted number of points, goals scored and goals conceded at the end of the season.
It also contains predictions for each teams likelihood to finish 1st, Top 4, Top 6 and Bottom 3, derived from running Monte Carlo simulations on the rest of the seasons fixtures.

## Corner Game State Analysis

This project looks at the effect that game state has on corner performances. It processes event level data to calculate how long each team spends in each game state and how many corners are won or conceded in each game state. 
It then examines the effect that these game state effects can have on corner performance and proposes a way of harnessing team supremacy and game state dynamics to create better corner ratings for use in predictive models.

## Dependencies

- See setup section below to install the required packages for these projects

## Setup

1. Clone the Repository
```
git clone https://github.com/lukechambers999/portfolio
cd portfolio
```
2. Create a Virtual Environment
```
python -m venv venv
source venv/bin/activate  # Windows use: venv\Scripts\activate
```
3. Install Required Packages
```
pip install -r requirements.txt
```
4. Launch Jupyter Notebook
```
jupyter notebook
```
Then navigate to and open any of the .ipynb files to explore the projects.

## Data

The following data files are used in this project:
- `data/'League'.csv`: Five individual files containing historical betting odds for top 5 leagues.
- `data/goallines.csv`: Contains a lookup table to convert betting lines into goal expectancies for each match.
- `data/supconversion.csv`: Contains a lookup table to convert betting lines into goal expectancies for each match.
- `data/mins_conv.csv`: Contains a lookup table to convert goal expectancies into expected winning, drawing and losing minutes for each match.
- `data/corner_gamestate.csv`: Contains event level data for a range of leagues for game state analysis.

These files are located in the `data/` folder.

In addition to these files the LT_model script scrapes historical and future fixture information using the Understat API

## Contact
For questions or feedback, feel free to reach out:
- luke.chambers999@gmail.com

