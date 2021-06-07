import matplotlib.pyplot as plot
from .functions import get_redditor_name, add_user
from .database_reader import delete_transcriber,fetch_transcribers

__all__ = ["get_redditor_name", "add_user", "delete_transcriber", "fetch_transcribers"]

# Colors to use in the plots
background_color = "#4e6186"
text_color = "white"
line_color = "gray"

# Global settings for the plots
plot.rcParams['figure.facecolor'] = background_color
plot.rcParams['axes.facecolor'] = background_color
plot.rcParams['axes.labelcolor'] = text_color
plot.rcParams['axes.edgecolor'] = line_color
plot.rcParams['text.color'] = text_color
plot.rcParams['xtick.color'] = line_color
plot.rcParams['ytick.color'] = line_color
plot.rcParams['grid.color'] = line_color
plot.rcParams['grid.alpha'] = 0.8
plot.rcParams["figure.dpi"] = 200.0
