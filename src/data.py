import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from pathlib import Path
import numpy as np

def generate_charts(db_path="data/stats.db", output_dir="data"):
    """
    Generate and save charts from database statistics using Matplotlib.
    
    Args:
        db_path (str): Path to the SQLite database
        output_dir (str): Directory to save generated charts
    
    Returns:
        dict: Information about generated charts
    """
    # Ensure output directory exists
    Path(output_dir).mkdir(exist_ok=True, parents=True)
    
    # Connect to the SQL database with error handling
    try:
        conn = sqlite3.connect(db_path)
        query = "SELECT * FROM stats"
        df = pd.read_sql_query(query, conn)
        conn.close()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return {"error": f"Database error: {e}"}
    except Exception as e:
        print(f"Error: {e}")
        return {"error": f"Error: {e}"}
    
    # Check if DataFrame is empty
    if df.empty:
        print("No data found in the database.")
        return {"error": "No data found in the database."}
    
    # Print columns and a sample of the DataFrame for debugging
    print("DataFrame columns:", df.columns)
    print(df.head())
    
    # Check if 'Name' column exists
    if 'Name' not in df.columns:
        print("Error: 'Name' column not found in database.")
        return {"error": "'Name' column not found in database."}
    
    # Generate charts for each category
    generated_charts = {}
    
    # Set high-quality figure properties
    plt.rcParams['figure.dpi'] = 300
    plt.rcParams['savefig.dpi'] = 300
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['axes.labelsize'] = 12
    
    # Generate individual category charts
    for category in df['Name'].unique():
        try:
            # Filter data for this category
            category_data = df[df['Name'] == category].drop('Name', axis=1).T.reset_index()
            category_data.columns = ['Entity', 'Value']
            
            # Create a figure with subplots
            fig, axs = plt.subplots(2, 2, figsize=(16, 12))
            axs = axs.flatten()
            
            # Bar Chart
            axs[0].bar(category_data['Entity'], category_data['Value'], color='steelblue')
            axs[0].set_title(f'{category} - Bar Chart')
            axs[0].set_xlabel('Entities')
            axs[0].set_ylabel('Values')
            axs[0].tick_params(axis='x', rotation=90)
            
            # Line Chart
            axs[1].plot(category_data['Entity'], category_data['Value'], 'o-', color='forestgreen', linewidth=2)
            axs[1].set_title(f'{category} - Line Chart')
            axs[1].set_xlabel('Entities')
            axs[1].set_ylabel('Values')
            axs[1].tick_params(axis='x', rotation=90)
            
            # Pie Chart
            # Only create pie chart if there are positive values
            if sum(category_data['Value']) > 0:
                axs[2].pie(category_data['Value'], labels=category_data['Entity'], autopct='%1.1f%%', startangle=90)
                axs[2].set_title(f'{category} - Pie Chart')
            else:
                axs[2].text(0.5, 0.5, 'No positive values for pie chart', ha='center', va='center')
                axs[2].set_title(f'{category} - Pie Chart')
                axs[2].axis('off')
            
            # Scatter Plot
            axs[3].scatter(range(len(category_data['Entity'])), category_data['Value'], color='darkorange', s=100)
            for i, (entity, value) in enumerate(zip(category_data['Entity'], category_data['Value'])):
                axs[3].annotate(f"{entity}: {value}", (i, value), xytext=(0, 5), textcoords='offset points', ha='center')
            axs[3].set_title(f'{category} - Scatter Plot')
            axs[3].set_xlabel('Entity Index')
            axs[3].set_ylabel('Values')
            
            # Adjust layout and save
            plt.tight_layout()
            chart_path = os.path.join(output_dir, f"{category}_charts.png")
            plt.savefig(chart_path)
            plt.close()
            
            generated_charts[category] = chart_path
            print(f"Generated chart for {category}: {chart_path}")
            
        except Exception as e:
            print(f"Error generating charts for {category}: {e}")
            plt.close()
    
    # Create combined charts for all categories
    try:
        # Prepare data for combined charts
        df_no_name = df.set_index('Name')
        
        # Create a figure with subplots for combined charts
        fig, axs = plt.subplots(2, 2, figsize=(18, 14))
        axs = axs.flatten()
        
        # Stacked Bar Chart
        df_no_name.T.plot(kind='bar', stacked=True, ax=axs[0], colormap='viridis')
        axs[0].set_title('Stacked Bar Chart - All Categories')
        axs[0].set_xlabel('Entities')
        axs[0].set_ylabel('Values')
        axs[0].tick_params(axis='x', rotation=90)
        axs[0].legend(title='Categories')
        
        # Line Chart
        df_no_name.T.plot(kind='line', ax=axs[1], marker='o', colormap='tab10')
        axs[1].set_title('Line Chart - All Categories')
        axs[1].set_xlabel('Entities')
        axs[1].set_ylabel('Values')
        axs[1].tick_params(axis='x', rotation=90)
        axs[1].legend(title='Categories')
        
        # Heatmap
        sns.heatmap(df_no_name, annot=True, cmap='YlGnBu', fmt='.0f', ax=axs[2])
        axs[2].set_title('Heatmap - All Categories')
        axs[2].set_xlabel('Entities')
        axs[2].set_ylabel('Categories')
        
        # Grouped Bar Chart
        df_no_name.T.plot(kind='bar', ax=axs[3], colormap='tab20')
        axs[3].set_title('Grouped Bar Chart - All Categories')
        axs[3].set_xlabel('Entities')
        axs[3].set_ylabel('Values')
        axs[3].tick_params(axis='x', rotation=90)
        axs[3].legend(title='Categories')
        
        # Adjust layout and save
        plt.tight_layout()
        all_charts_path = os.path.join(output_dir, "all_categories_charts.png")
        plt.savefig(all_charts_path)
        plt.close()
        
        generated_charts["all_categories"] = all_charts_path
        print(f"Generated combined charts: {all_charts_path}")
        
    except Exception as e:
        print(f"Error generating combined charts: {e}")
        plt.close()
    
    print("All charts have been saved as high-quality PNG images with improved text readability.")
    return {"success": True, "charts": generated_charts}

if __name__ == "__main__":
    result = generate_charts()
    print(f"Chart generation complete: {result}")