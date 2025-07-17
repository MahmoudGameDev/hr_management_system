# c:\Users\mahmo\OneDrive\Documents\GitHub\hr_management_system\utils\chart_utils.py
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import List, Dict, Any, Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)

def create_bar_chart(ax: Axes, data: Dict[str, Union[int, float]], title: str, xlabel: str, ylabel: str,
                     bar_colors: Optional[List[str]] = None, rotation: int = 0,
                     grid: bool = True, grid_axis: str = 'y', grid_style: str = '--', grid_alpha: float = 0.7):
    """
    Creates a bar chart on the given Matplotlib Axes object.

    Args:
        ax (Axes): The Matplotlib Axes to draw on.
        data (Dict[str, Union[int, float]]): Dictionary where keys are x-axis labels and values are y-axis values.
        title (str): Title of the chart.
        xlabel (str): Label for the x-axis.
        ylabel (str): Label for the y-axis.
        bar_colors (Optional[List[str]]): List of colors for the bars. Cycles if fewer colors than bars.
        rotation (int): Rotation angle for x-axis labels.
        grid (bool): Whether to display a grid.
        grid_axis (str): Which axis to apply the grid to ('x', 'y', 'both').
        grid_style (str): Linestyle for the grid.
        grid_alpha (float): Alpha transparency for the grid.
    """
    ax.clear() # Clear previous content
    labels = list(data.keys())
    values = list(data.values())

    if not bar_colors:
        bar_colors = ['skyblue'] # Default color

    bars = ax.bar(labels, values, color=[bar_colors[i % len(bar_colors)] for i in range(len(values))])
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis='x', rotation=rotation)
    if grid:
        ax.grid(True, axis=grid_axis, linestyle=grid_style, alpha=grid_alpha)
    # Optional: Add value labels on top of bars
    # for bar in bars:
    #     yval = bar.get_height()
    #     ax.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.2f}', va='bottom', ha='center') # va: vertical alignment

def create_pie_chart(ax: Axes, data: Dict[str, Union[int, float]], title: str,
                     pie_colors: Optional[List[str]] = None, autopct: str = '%1.1f%%', startangle: int = 90):
    """
    Creates a pie chart on the given Matplotlib Axes object.

    Args:
        ax (Axes): The Matplotlib Axes to draw on.
        data (Dict[str, Union[int, float]]): Dictionary where keys are labels and values are sizes.
        title (str): Title of the chart.
        pie_colors (Optional[List[str]]): List of colors for the slices. Cycles if fewer colors than slices.
        autopct (str): Format string for percentage display on slices.
        startangle (int): Angle at which the first slice starts.
    """
    ax.clear()
    labels = list(data.keys())
    sizes = list(data.values())

    if not pie_colors:
        pie_colors = plt.cm.Paired.colors # Default color map

    ax.pie(sizes, labels=labels, autopct=autopct, startangle=startangle,
           colors=[pie_colors[i % len(pie_colors)] for i in range(len(sizes))])
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    ax.set_title(title)

def create_line_chart(ax: Axes, x_data: List[Any], y_data: List[Union[int, float]], title: str,
                      xlabel: str, ylabel: str, line_color: str = 'blue', marker: Optional[str] = 'o',
                      grid: bool = True, grid_axis: str = 'y', grid_style: str = '--', grid_alpha: float = 0.7):
    """
    Creates a line chart on the given Matplotlib Axes object.

    Args:
        ax (Axes): The Matplotlib Axes to draw on.
        x_data (List[Any]): Data for the x-axis.
        y_data (List[Union[int, float]]): Data for the y-axis.
        title (str): Title of the chart.
        xlabel (str): Label for the x-axis.
        ylabel (str): Label for the y-axis.
        line_color (str): Color of the line.
        marker (Optional[str]): Marker style for data points (e.g., 'o', 's', '^').
        grid (bool): Whether to display a grid.
        grid_axis (str): Which axis to apply the grid to ('x', 'y', 'both').
        grid_style (str): Linestyle for the grid.
        grid_alpha (float): Alpha transparency for the grid.
    """
    ax.clear()
    ax.plot(x_data, y_data, color=line_color, marker=marker)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if grid:
        ax.grid(True, axis=grid_axis, linestyle=grid_style, alpha=grid_alpha)
    ax.tick_params(axis='x', rotation=45) # Rotate x-axis labels for better readability if they are dates/long strings