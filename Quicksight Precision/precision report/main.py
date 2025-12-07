
import pandas as pd
import openpyxl
from openpyxl import load_workbook
import os
import tkinter as tk
from tkinter import filedialog, messagebox

def pivot_for_quicksight(data, columns):
    """
    Convert wide format data to long format with separate Month and metric columns.
    """
    # Identify month-metric columns and ID columns
    month_metric_cols = []
    id_cols = []
    
    for col in columns:
        # Check if column contains month indicators
        if any(month in col.upper() for month in ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 
                                                   'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']):
            month_metric_cols.append(col)
        else:
            id_cols.append(col)
    
    # Group columns by month and metric
    month_data = {}
    
    for col in month_metric_cols:
        # Extract month and metric from column name
        parts = col.split('_', 1)
        if len(parts) >= 2:
            month = parts[0]
            metric = parts[1]
            
            # Clean up metric name
            metric = metric.replace('_', ' ')
            metric = metric.replace('ISW WTS InfluencerLLM Audit Counts', 'ISW+WTS+Influencer+LLM Audit Counts')
            metric = metric.replace('Makers TP Counts', 'Makers TP Counts')
            metric = metric.replace('Suppression Count', 'Suppression Count')
            metric = metric.replace('Precision Percent', 'Precision %')
            metric = metric.replace('Variance', 'Variance')
            
            if month not in month_data:
                month_data[month] = {}
            month_data[month][metric] = col
    
    # Create long format data
    long_data = []
    
    for idx, row in data.iterrows():
        # Get ID values for this row
        id_values = {}
        for id_col in id_cols:
            if id_col in data.columns:
                id_values[id_col] = row[id_col]
        
        # Create a row for each month
        for month, metrics in month_data.items():
            row_data = {'Month': month.replace('25', "'25")}  # Format month as Jan'25
            row_data.update(id_values)  # Add ID columns
            
            # Add each metric as separate column
            for metric_name, col_name in metrics.items():
                if col_name in data.columns:
                    row_data[metric_name] = row[col_name]
            
            long_data.append(row_data)
    
    return pd.DataFrame(long_data)

def convert_merged_headers_to_quicksight(input_file, output_file=None, sheet_name=0, header_rows=2):
    """
    Convert Excel file with merged cell headers to QuickSight-ready format.
    
    Parameters:
    - input_file: Path to input Excel file
    - output_file: Path to output Excel file (if None, creates '_quicksight' version)
    - sheet_name: Sheet name or index to process (default: 0 for first sheet)
    - header_rows: Number of header rows to combine (default: 2)
    """
    
    # Read the Excel file
    df = pd.read_excel(input_file, sheet_name=sheet_name, header=None)
    
    # Extract header rows and data
    headers = df.iloc[:header_rows].copy()
    data = df.iloc[header_rows:].copy()
    
    # Create new column names by handling merged cells properly
    new_columns = []
    
    # First, identify merged month headers in the first row
    month_headers = {}
    current_month = None
    
    for col_idx in range(len(df.columns)):
        value = headers.iloc[0, col_idx]
        if pd.notna(value) and str(value).strip():
            current_month = str(value).strip()
        month_headers[col_idx] = current_month
    
    # Now create column names combining month with other header rows
    for col_idx in range(len(df.columns)):
        col_parts = []
        
        # Add month from merged cell
        if month_headers[col_idx]:
            col_parts.append(month_headers[col_idx])
        
        # Collect values from remaining header rows (skip first row as it's month)
        for row_idx in range(1, header_rows):
            value = headers.iloc[row_idx, col_idx]
            if pd.notna(value) and str(value).strip():
                col_parts.append(str(value).strip())
        
        # Combine parts
        if not col_parts:
            new_column = f"Column_{col_idx + 1}"
        else:
            # Join with underscore
            new_column = "_".join(col_parts)
            
            # Clean up for QuickSight compatibility
            new_column = new_column.replace(" ", "_")
            new_column = new_column.replace("+", "")
            new_column = new_column.replace("'", "")
            new_column = new_column.replace("%", "Percent")
            new_column = new_column.replace("&", "and")
            new_column = new_column.replace("-", "_")
            
            # Remove multiple underscores
            while "__" in new_column:
                new_column = new_column.replace("__", "_")
            new_column = new_column.strip("_")
        
        new_columns.append(new_column)
    
    # Apply new headers
    data.columns = new_columns
    data = data.reset_index(drop=True)
    
    # Determine output file name
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_quicksight.xlsx"
    
    # Pivot data to long format for QuickSight
    pivoted_data = pivot_for_quicksight(data, new_columns)
    
    # Save to new Excel file
    pivoted_data.to_excel(output_file, index=False, sheet_name='Data')
    
    print(f"✓ Converted file saved to: {output_file}")
    print(f"✓ Data pivoted to long format with Month column")
    print(f"✓ Total rows: {len(pivoted_data)}")
    
    return pivoted_data, new_columns


def convert_multiple_sheets(input_file, output_file=None, header_rows=2):
    """
    Convert all sheets in an Excel file to QuickSight-ready format.
    """
    
    # Get all sheet names
    xl_file = pd.ExcelFile(input_file)
    sheet_names = xl_file.sheet_names
    
    # Determine output file name
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_quicksight.xlsx"
    
    # Create Excel writer
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for sheet_name in sheet_names:
            print(f"Processing sheet: {sheet_name}")
            try:
                # Read the sheet
                df = pd.read_excel(input_file, sheet_name=sheet_name, header=None)
                
                # Extract headers and data
                headers = df.iloc[:header_rows].copy()
                data = df.iloc[header_rows:].copy()
                
                # Create new column names by handling merged cells properly
                new_columns = []
                
                # First, identify merged month headers in the first row
                month_headers = {}
                current_month = None
                
                for col_idx in range(len(df.columns)):
                    value = headers.iloc[0, col_idx]
                    if pd.notna(value) and str(value).strip():
                        current_month = str(value).strip()
                    month_headers[col_idx] = current_month
                
                # Now create column names combining month with other header rows
                for col_idx in range(len(df.columns)):
                    col_parts = []
                    
                    # Add month from merged cell
                    if month_headers[col_idx]:
                        col_parts.append(month_headers[col_idx])
                    
                    # Collect values from remaining header rows (skip first row as it's month)
                    for row_idx in range(1, header_rows):
                        value = headers.iloc[row_idx, col_idx]
                        if pd.notna(value) and str(value).strip():
                            col_parts.append(str(value).strip())
                    
                    if not col_parts:
                        new_column = f"Column_{col_idx + 1}"
                    else:
                        new_column = "_".join(col_parts)
                        new_column = new_column.replace(" ", "_")
                        new_column = new_column.replace("+", "")
                        new_column = new_column.replace("'", "")
                        new_column = new_column.replace("%", "Percent")
                        new_column = new_column.replace("&", "and")
                        new_column = new_column.replace("-", "_")
                        while "__" in new_column:
                            new_column = new_column.replace("__", "_")
                        new_column = new_column.strip("_")
                    
                    new_columns.append(new_column)
                
                # Apply new headers
                data.columns = new_columns
                data = data.reset_index(drop=True)
                
                # Pivot data to long format for QuickSight
                pivoted_data = pivot_for_quicksight(data, new_columns)
                
                # Write to Excel
                pivoted_data.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"✓ Sheet '{sheet_name}' converted successfully ({len(new_columns)} columns)")
                
            except Exception as e:
                print(f"✗ Error processing sheet '{sheet_name}': {str(e)}")
    
    print(f"✓ All sheets converted and saved to: {output_file}")


def select_and_convert():
    """Interactive file selection and conversion."""
    print("Starting Excel to QuickSight converter...")
    
    try:
        # Hide the main tkinter window
        root = tk.Tk()
        root.withdraw()
        
        print("Opening file dialog...")
        
        # Select input file
        input_file = filedialog.askopenfilename(
            title="Select Excel file to convert",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        
        if not input_file:
            print("No file selected. Exiting.")
            root.destroy()
            return
        
        print(f"Selected file: {input_file}")
        
        # Ask for processing options
        choice = input("\nChoose conversion type:\n1. Single sheet (default)\n2. All sheets\nEnter choice (1 or 2): ").strip()
        
        header_rows = input("Number of header rows to combine (default: 2): ").strip()
        header_rows = int(header_rows) if header_rows.isdigit() else 2
        
        if choice == "2":
            convert_multiple_sheets(input_file, header_rows=header_rows)
        else:
            convert_merged_headers_to_quicksight(input_file, header_rows=header_rows)
            
        root.destroy()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Excel to QuickSight Header Converter")
    print("====================================")
    select_and_convert()
    input("\nPress Enter to exit...")


