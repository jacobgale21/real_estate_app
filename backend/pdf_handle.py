
import pandas as pd
import PyPDF2
import os
import re
import tempfile
from pathlib import Path
# Write DataFrames to PDF in minimal lines
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, ListFlowable, ListItem
import matplotlib.pyplot as plt
from reportlab.platypus import Image, PageBreak
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
import shutil
from typing import List, Dict, Any
import json
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from middleware import verify_token, verify_token_query
from llm_api import generate_chatgpt_prompt_mini, generate_chatgpt_prompt_features, get_feature_list

def extract_property_type(file_path):
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if 'residential customer report' in text.lower():
                return "Residential"
            else:
                return "Rental"

def extract_property_info(file_path):
    """
    Extract property information from PDF text.
    Each MLS report contains the same phrases for basic property information, so use regex statements to extract basic information.

    Args:
        text (str): Extracted text from PDF
        
    Returns:
        dict: Dictionary containing extracted property information
    """
    rental_report = False
    try:
        with open(file_path, 'rb') as file:
            # Create PDF reader object
            pdf_reader = PyPDF2.PdfReader(file)

            property_result = []
            price_result = []
            features_result = []
            # Loop through each page of the PDF
            for page_num, page in enumerate(pdf_reader.pages):
                # Extract text from the page
                text = page.extract_text()
                # Check if the first line contains residentialcustomer report
                if 'residential customer report' in text.lower(): 
                    # Initialize dictionaries to store property and price information
                    property_info = {
                        'Address': None,
                        'Status': None,
                        'Subdivision': None,
                        'Year Built': None,
                        'Living Sq Ft': None,
                        'Total Sq Ft': None,
                        'Bedrooms': None,
                        'Bathrooms (Full)': None,
                        'Stories': None,
                        'Garage Spaces': None,
                        'Private Pool': None,
                        
                    }
                    features_info = {
                        'Address': None,
                        'Private Pool Description': None,
                        'Interior': None,
                        'Exterior': None,
                        'Public Remarks': None
                    }

                    price_info = {
                        'Address': None,
                        'List Price': None,
                        'List $/Sq Ft (Living)': None,
                        'Sold Price': None,
                        'Sold $/Sq Ft (Living)': None,
                        'DOM': None
                    }

                    lines = text.split('\n')
                    
                    # Iterate through each line of the text and extract the property and price information through regex statements
                    for line in lines:
                        if 'residential customer report' in line.lower():
                            address_match = re.search(r"report\s*(.*?)\s*(?:,|$)", line, re.IGNORECASE)
                            if address_match:
                                price_info['Address'] = address_match.group(1).strip()
                                property_info['Address'] = address_match.group(1).strip()
                                features_info['Address'] = address_match.group(1).strip()
                        if 'subdivision:' in line.lower():
                            subdivision_match = re.search(r'subdivision:\s*(.+)', line, re.IGNORECASE)
                            if subdivision_match:
                                property_info['Subdivision'] = subdivision_match.group(1).strip()
                        elif 'livsqft' in line.lower():
                            living_sq_ft_match = re.search(r'livsqft:\s*(.+)', line, re.IGNORECASE)
                            if living_sq_ft_match:
                                property_info['Living Sq Ft'] = living_sq_ft_match.group(1).strip()
                        elif 'sqft - total' in line.lower():
                            total_sq_ft_match = re.search(r'sqft - total:\s*(.+)', line, re.IGNORECASE)
                            if total_sq_ft_match:
                                property_info['Total Sq Ft'] = total_sq_ft_match.group(1).strip()
                        elif 'yr built' in line.lower():
                            year_built_match = re.search(r'yr built:\s*(.+)', line, re.IGNORECASE)
                            if year_built_match:
                                property_info['Year Built'] = year_built_match.group(1).strip()
                        elif 'baths - total' in line.lower():
                            baths_total_match = re.search(r'baths - total:\s*(.+)', line, re.IGNORECASE)
                            if baths_total_match:
                                property_info['Bathrooms (Full)'] = baths_total_match.group(1).strip()
                        elif 'total bedrooms' in line.lower():
                            total_bedrooms_match = re.search(r'total bedrooms:\s*(.+)', line, re.IGNORECASE)
                            if total_bedrooms_match:
                                property_info['Bedrooms'] = total_bedrooms_match.group(1).strip()
                        elif 'private pool description' in line.lower():
                            private_pool_description_match = re.search(r'private pool description:(.+)', line, re.IGNORECASE)
                            if private_pool_description_match:
                                features_info['Private Pool Description'] = private_pool_description_match.group(1).strip()
                        elif 'private pool' in line.lower():
                            private_pool_match = re.search(r'private pool:\s*(.+)', line, re.IGNORECASE)
                            if private_pool_match:
                                property_info['Private Pool'] = private_pool_match.group(1).strip()
                        elif 'stories' in line.lower():
                            stories_match = re.search(r'stories:\s*(.+)', line, re.IGNORECASE)
                            if stories_match:
                                property_info['Stories'] = stories_match.group(1).strip()
                        elif 'spaces' in line.lower():
                            garage_match = re.search(r'spaces:\s*(.+)', line, re.IGNORECASE)
                            if garage_match:
                                property_info['Garage Spaces'] = garage_match.group(1).strip()
                        elif 'orig lp' in line.lower():
                            # Extract list price between "orig lp:" and "list price/sqft:"
                            orig_lp_match = re.search(r"lp:\s+(.*?)\s+list price", line, re.IGNORECASE)
                            orig_sqft_match = re.search(r'list price/sqft:\s*(.+)', line, re.IGNORECASE)
                            if orig_lp_match:
                                price_info['List Price'] = orig_lp_match.group(1).strip()
                            if orig_sqft_match:
                                price_info['List $/Sq Ft (Living)'] = orig_sqft_match.group(1).strip()
                        elif 'sold price' in line.lower():
                            sold_price_match = re.search(r"sold price:\s+(.*?)\s+sold price sqft", line, re.IGNORECASE)
                            if sold_price_match:
                                price_info['Sold Price'] = sold_price_match.group(1).strip()
                            sold_price_sqft_match = re.search(r'sold price sqft:\s*(.+)', line, re.IGNORECASE)
                            if sold_price_sqft_match:
                                price_info['Sold $/Sq Ft (Living)'] = sold_price_sqft_match.group(1).strip()
                        elif 'days on market' in line.lower():
                            days_on_market_match = re.search(r'days on market:\s*(.+)', line, re.IGNORECASE)
                            if days_on_market_match:
                                price_info['DOM'] = days_on_market_match.group(1).strip()
                        elif 'st:' in line.lower():
                            status_match = re.search(r'st:\s+(.*?)\s+type', line, re.IGNORECASE)
                            if status_match:
                                property_info['Status'] = status_match.group(1).strip()
                        elif 'interior' in line.lower():
                            interior_match = re.search(r'interior:(.*)', line, re.IGNORECASE)
                            if interior_match:
                                features_info['Interior'] = interior_match.group(1).strip()
                        elif 'exterior' in line.lower():
                            exterior_match = re.search(r'exterior:(.*)', line, re.IGNORECASE)
                            if exterior_match:
                                features_info['Exterior'] = exterior_match.group(1).strip()
                        elif 'public remarks' in line.lower():
                            # Start collecting public remarks from this line
                            remarks_start = line.find(':') + 1 if ':' in line else 0
                            remarks_text = line[remarks_start:].strip()
                            
                            # Continue reading subsequent lines until we hit another section
                            line_index = lines.index(line) + 1
                            while line_index < len(lines):
                                next_line = lines[line_index].strip()
                                # Stop if we hit another section (usually starts with a field name and colon)
                                if (next_line and 
                                    any(keyword in next_line.lower() for keyword in 
                                        ['charles gale'])):
                                    break
                                if next_line:  # Only add non-empty lines
                                    remarks_text += ' ' + next_line
                                line_index += 1
                            
                            features_info['Public Remarks'] = remarks_text.strip()
                    property_result.append(property_info)
                    features_result.append(features_info)
                    price_result.append(price_info)
                # Process rental property report
                elif "rental customer report" in text.lower():
                    rental_report = True
                        # Initialize dictionaries to store property and price information
                    property_info = {
                        'Address': None,
                        'Status': None,
                        'Subdivision': None,
                        'Year Built': None,
                        'Living Sq Ft': None,
                        'Total Sq Ft': None,
                        'Bedrooms': None,
                        'Bathrooms (Full)': None,
                        'Stories': None,
                        'Garage Spaces': None,
                        'Private Pool': None,
                        
                    }
                    features_info = {
                        'Private Pool Description': None,
                        'Interior': None,
                        'Exterior': None,
                        'Public Remarks': None,
                         
                    }

                    price_info = {
                        'Address': None,
                        'List Price': None,
                        'List $/Sq Ft (Living)': None,
                        'Sold Price': None,
                        'Sold $/Sq Ft (Living)': None,
                        'DOM': None
                    }

                    lines = text.split('\n')
                    
                    # Iterate through each line of the text and extract the property and price information through regex statements
                    for line in lines:
                        if 'subdivision:' in line.lower():
                            subdivision_match = re.search(r'subdivision:\s*(.+)\s+front exposure', line, re.IGNORECASE)
                            if subdivision_match:
                                property_info['Subdivision'] = subdivision_match.group(1).strip()
                        elif 'sqft - living' in line.lower():
                            living_sq_ft_match = re.search(r'sqft - living:\s*(.+)\s+total units', line, re.IGNORECASE)
                            if living_sq_ft_match:
                                property_info['Living Sq Ft'] = living_sq_ft_match.group(1).strip()
                        elif 'sqft - total' in line.lower():
                            total_sq_ft_match = re.search(r'sqft - total:\s*(.+)\s+unit floor', line, re.IGNORECASE)
                            if total_sq_ft_match:
                                property_info['Total Sq Ft'] = total_sq_ft_match.group(1).strip()
                        elif 'year built' in line.lower():
                            year_built_match = re.search(r'year built:\s*(.+)\s+for sale', line, re.IGNORECASE)
                            if year_built_match:
                                property_info['Year Built'] = year_built_match.group(1).strip()
                        elif 'baths - total' in line.lower():
                            baths_total_match = re.search(r'baths - total:\s*(.+)\s+private pool', line, re.IGNORECASE)
                            if baths_total_match:
                                property_info['Bathrooms (Full)'] = baths_total_match.group(1).strip()
                            private_pool_match = re.search(r'private pool:\s*(.+)', line, re.IGNORECASE)
                            if private_pool_match:
                                property_info['Private Pool'] = private_pool_match.group(1).strip()
                        elif 'total bedrooms' in line.lower():
                            total_bedrooms_match = re.search(r'total bedrooms:\s*(.+)\s+governing', line, re.IGNORECASE)
                            if total_bedrooms_match:
                                property_info['Bedrooms'] = total_bedrooms_match.group(1).strip()
                        elif 'total floors in bldg' in line.lower():
                            stories_match = re.search(r'total floors in bldg:\s*(.+)', line, re.IGNORECASE)
                            if stories_match:
                                property_info['Stories'] = stories_match.group(1).strip()
                        elif 'garage spaces' in line.lower():
                            garage_match = re.search(r'garage spaces:\s*(.+)\s+membership', line, re.IGNORECASE)
                            if garage_match:
                                property_info['Garage Spaces'] = garage_match.group(1).strip()
                        elif 'orig. lp' in line.lower():
                            # Extract list price between "orig lp:" and "list price/sqft:"
                            status_match = re.search(r'st:\s+(.*?)\s+orig. lp', line, re.IGNORECASE)
                            if status_match:
                                property_info['Status'] = status_match.group(1).strip()
                        elif 'rental price' in line.lower():
                            address_match = re.search(r"report\s*(.*?)\s*(?:,|$)", line, re.IGNORECASE)
                            if address_match:
                                price_info['Address'] = address_match.group(1).strip()
                                property_info['Address'] = address_match.group(1).strip()
                                features_info['Address'] = address_match.group(1).strip()
                            sold_price_match = re.search(r"rental price:\s*(.+)", line, re.IGNORECASE)
                            if sold_price_match:
                                price_info['List Price'] = sold_price_match.group(1).strip()
                        elif 'days on market' in line.lower():
                            days_on_market_match = re.search(r'days on market:\s*(.+)', line, re.IGNORECASE)
                            if days_on_market_match:
                                price_info['DOM'] = days_on_market_match.group(1).strip()
                        elif 'interior features' in line.lower():
                            interior_match = re.search(r'interior features:(.*)', line, re.IGNORECASE)
                            if interior_match:
                                features_info['Interior'] = interior_match.group(1).strip()
                        elif 'exterior features' in line.lower():
                            exterior_match = re.search(r'exterior features:(.*)', line, re.IGNORECASE)
                            if exterior_match:
                                features_info['Exterior'] = exterior_match.group(1).strip()
                        elif 'public remarks' in line.lower():
                            # Start collecting public remarks from this line
                            remarks_start = line.find(':') + 1 if ':' in line else 0
                            remarks_text = line[remarks_start:].strip()
                            
                            # Continue reading subsequent lines until we hit another section
                            line_index = lines.index(line) + 1
                            while line_index < len(lines):
                                next_line = lines[line_index].strip()
                                # Stop if we hit another section (usually starts with a field name and colon)
                                if (next_line and 
                                    any(keyword in next_line.lower() for keyword in 
                                        ['charles gale'])):
                                    break
                                if next_line:  # Only add non-empty lines
                                    remarks_text += ' ' + next_line
                                line_index += 1
                            
                            features_info['Public Remarks'] = remarks_text.strip()
                    price_info['List $/Sq Ft (Living)'] = pd.to_numeric(price_info['List Price'].replace('$', '').replace(',', ''), errors='coerce') / pd.to_numeric(property_info['Living Sq Ft'].replace(',', ''), errors='coerce')
                    property_result.append(property_info)
                    features_result.append(features_info)
                    price_result.append(price_info)
            return property_result, price_result, features_result, rental_report
    
    except Exception as e:
        print(f"Error reading PDF file {file_path}: {e}")
        return None

def generate_chatgpt_prompt(property_info, price_info, features_info):
    prompt = f"""
    You are a professional real estate market analyst specializing in MLS-based comparative market reports. 
    Your job is to create a detailed, appraisal-style markdown report comparing a subject property against multiple comparable sales. 
    Follow the exact structure below:
    1. Size & Price Positioning
    2. Notable Feature Comparisons
    3. Market Context & Value Implications
    4. Appraisal Perspective
    5. Summary
    Include markdown tables for data and bullet points for observations. Be precise in calculations.\n\n"""
    for idx, row in property_info.iterrows():
        prompt += f"Property {idx + 1}:\n"
        for key, value in row.items():
            prompt += f"{key}: {value} | "
        for key, value in price_info.iloc[idx].items():
            if key != 'Address':
                prompt += f"{key}: {value} | "
        for key, value in features_info.iloc[idx].items():
            if key != 'Address':
                prompt += f"{key}: {value} | "
        prompt += "\n\n"
    prompt += f"Please produce the full appraisal-style comparison for the subject property: {property_info['Address'].iloc[0]} versus the other {len(property_info) - 1} properties. Follow the section structure exactly."
    return prompt



def generate_graphs(combined_df_price, is_rental):
    # Clean data by removing None values and converting to numeric
    if is_rental:
        try:
            df_clean = combined_df_price.copy()
            # Convert price columns to numeric, removing $ and commas
            for col in ['List Price']:
                df_clean[col] = pd.to_numeric(df_clean[col].str.replace('$', '').str.replace(',', ''), errors='coerce')
            for col in ['List $/Sq Ft (Living)']:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
            
            # Remove rows where both values are None/NaN
            df_clean = df_clean.dropna(subset=['List Price'])
            # Filter for properties with both list and sold prices
            valid_data = df_clean.dropna(subset=['List Price'])

            if not valid_data.empty:
                addresses = valid_data['Address'].tolist()
                list_prices = valid_data['List Price'].tolist()
                
                x = range(len(addresses))
                width = 0.35
            
                plt.bar([i - width/2 for i in x], list_prices, width, label='List Price', color='skyblue', alpha=0.8)
                plt.xlabel('Properties')
                plt.ylabel('Price ($/Month)')
                plt.title('Rental Price Comparison')
                plt.xticks(x, [addr.split()[0] + ' ' + addr.split()[1] if len(addr.split()) > 1 else addr for addr in addresses], rotation=45, ha='right')
                plt.legend()
                plt.tight_layout()
                plt.savefig(os.path.join(temp_dir, 'list_price_vs_sold_price.png'), dpi=300, bbox_inches='tight')
                

            # List $/Sq Ft vs Sold $/Sq Ft Bar Chart
            plt.figure(figsize=(12, 8))

            valid_sqft_data = df_clean.dropna(subset=['List $/Sq Ft (Living)'])
            if not valid_sqft_data.empty:
                addresses_sqft = valid_sqft_data['Address'].tolist()
                list_sqft = valid_sqft_data['List $/Sq Ft (Living)'].tolist()
                
                x_sqft = range(len(addresses_sqft))
                width = 0.35
                
                plt.bar([i - width/2 for i in x_sqft], list_sqft, width, label='List $/Sq Ft', color='lightgreen', alpha=0.8)
                
                plt.xlabel('Properties')
                plt.ylabel('Price per Sq Ft ($)')
                plt.title('List \$/ Sq Ft Comparison')
                plt.xticks(x_sqft, [addr.split()[0] + ' ' + addr.split()[1] if len(addr.split()) > 1 else addr for addr in addresses_sqft], rotation=45, ha='right')
                plt.legend()
                plt.tight_layout()
                plt.savefig(os.path.join(temp_dir, 'list_price_sqft_vs_sold_price_sqft.png'), dpi=300, bbox_inches='tight')
        except Exception as e:
            print(f"Error generating rental graphs: {e}")
            return None
    else:
        try:
            df_clean = combined_df_price.copy()

            # Convert price columns to numeric, removing $ and commas
            for col in ['List Price', 'Sold Price']:
                df_clean[col] = pd.to_numeric(df_clean[col].str.replace('$', '').str.replace(',', ''), errors='coerce')

            for col in ['List $/Sq Ft (Living)', 'Sold $/Sq Ft (Living)']:
                df_clean[col] = pd.to_numeric(df_clean[col].str.replace('$', '').str.replace(',', ''), errors='coerce')

            # Remove rows where both values are None/NaN
            df_clean = df_clean.dropna(subset=['List Price', 'Sold Price'], how='all')


            # Filter for properties with both list and sold prices
            valid_data = df_clean

            if not valid_data.empty:
                addresses = valid_data['Address'].tolist()
                list_prices = valid_data['List Price'].tolist()
                sold_prices = valid_data['Sold Price'].tolist()
                
                x = range(len(addresses))
                width = 0.35
            
                plt.bar([i - width/2 for i in x], list_prices, width, label='List Price', color='skyblue', alpha=0.8)
                plt.bar([i + width/2 for i in x], sold_prices, width, label='Sold Price', color='lightcoral', alpha=0.8)         
                plt.xlabel('Properties')
                plt.ylabel('Price ($ MM)')
                plt.title('List Price vs Sold Price Comparison')
                plt.xticks(x, [addr.split()[0] + ' ' + addr.split()[1] if len(addr.split()) > 1 else addr for addr in addresses], rotation=45, ha='right')
                plt.legend()
                plt.tight_layout()
                plt.savefig(os.path.join(temp_dir, 'list_price_vs_sold_price.png'), dpi=300, bbox_inches='tight')
                

            # List $/Sq Ft vs Sold $/Sq Ft Bar Chart
            plt.figure(figsize=(12, 8))

            # Filter for properties with both list and sold price per sq ft
            valid_sqft_data = df_clean.dropna(subset=['List $/Sq Ft (Living)', 'Sold $/Sq Ft (Living)'], how='all')

            if not valid_sqft_data.empty:
                addresses_sqft = valid_sqft_data['Address'].tolist()
                list_sqft = valid_sqft_data['List $/Sq Ft (Living)'].tolist()
                sold_sqft = valid_sqft_data['Sold $/Sq Ft (Living)'].tolist()
                
                x_sqft = range(len(addresses_sqft))
                width = 0.35
                
                plt.bar([i - width/2 for i in x_sqft], list_sqft, width, label='List $/Sq Ft', color='lightgreen', alpha=0.8)
                plt.bar([i + width/2 for i in x_sqft], sold_sqft, width, label='Sold $/Sq Ft', color='orange', alpha=0.8)
                plt.xlabel('Properties')
                plt.ylabel('Price per Sq Ft ($)')
                plt.title('List \$/ Sq Ft vs Sold \$/ Sq Ft Comparison')
                plt.xticks(x_sqft, [addr.split()[0] + ' ' + addr.split()[1] if len(addr.split()) > 1 else addr for addr in addresses_sqft], rotation=45, ha='right')
                plt.legend()
                plt.tight_layout()
                plt.savefig(os.path.join(temp_dir, 'list_price_sqft_vs_sold_price_sqft.png'), dpi=300, bbox_inches='tight')
        except Exception as e:
            print(f"Error generating graphs: {e}")
            return None


def cleanup_temp_files():
    """Clean up all temporary files except the final report"""
    try:
        # Clean up uploaded PDFs
        for file_info in uploaded_files.values():
            if os.path.exists(file_info["file_path"]):
                os.remove(file_info["file_path"])
        
        # Clean up generated graphs
        graph_files = [
            os.path.join(temp_dir, 'list_price_vs_sold_price.png'),
            os.path.join(temp_dir, 'list_price_sqft_vs_sold_price_sqft.png')
        ]
        for graph_file in graph_files:
            if os.path.exists(graph_file):
                os.remove(graph_file)
        
        # Clear uploaded files dictionary
        uploaded_files.clear()
    except Exception as e:
        print(f"Error cleaning up temporary files: {e}")

def generate_appraisal_report(combined_df_price, input_sq_ft, is_rental):
    # Compare the average of the other properties to the target property
    # Calculate the average of the other properties
    # List containing inputs
    try:
        result = []
        # Remove commas from input_sq_ft and convert to integer
        input_sq_ft = int(input_sq_ft.replace(',', ''))
        if not is_rental:
            # Convert price columns to numeric, removing $ and commas
            for col in ['List Price', 'Sold Price']:
                combined_df_price[col] = pd.to_numeric(combined_df_price[col].str.replace('$', '').str.replace(',', ''), errors='coerce')

            for col in ['List $/Sq Ft (Living)', 'Sold $/Sq Ft (Living)']:
                # Check if the column contains string data (object dtype usually indicates strings)
                if combined_df_price[col].dtype == 'object':
                    combined_df_price[col] = pd.to_numeric(combined_df_price[col].str.replace('$', '').str.replace(',', ''), errors='coerce')
            
        
            # Exclude the first index (input property) and calculate mean of remaining comparison properties
            comparison_mean = combined_df_price['Sold $/Sq Ft (Living)'].iloc[1:].mean()
            estimated_value = input_sq_ft * comparison_mean
            result.append(f"Using the {len(combined_df_price) - 1} comparable properties, the average sold $/sq ft = ${comparison_mean:.2f}.")
            result.append(f"Applying this to {combined_df_price['Address'].iloc[0]}'s {input_sq_ft} sq ft yields an estimated value of ~ ${estimated_value:.2f}.")
            result.append(f"{combined_df_price['Address'].iloc[0]} ask of ${combined_df_price['List Price'].iloc[0]:,.0f} is {combined_df_price['List Price'].iloc[0]/estimated_value:.2f} times the estimated value.")
            return result
        else:
            for col in ['List Price']:
                combined_df_price[col] = pd.to_numeric(combined_df_price[col].str.replace('$', '').str.replace(',', ''), errors='coerce')

            for col in ['List $/Sq Ft (Living)']:
                # Check if the column contains string data (object dtype usually indicates strings)
               combined_df_price[col] = pd.to_numeric(combined_df_price[col], errors='coerce')
            # Exclude the first index (input property) and calculate mean of remaining comparison properties
            comparison_mean = combined_df_price['List $/Sq Ft (Living)'].iloc[1:].mean()
            estimated_value = input_sq_ft * comparison_mean
            result.append(f"Using the {len(combined_df_price) - 1} comparable properties, the average list $/sq ft = ${comparison_mean:.2f}.")
            result.append(f"Applying this to {combined_df_price['Address'].iloc[0]}'s {input_sq_ft} sq ft yields an estimated value of ~ ${estimated_value:.2f}.")
            result.append(f"{combined_df_price['Address'].iloc[0]} ask of ${combined_df_price['List Price'].iloc[0]:,.0f} is {combined_df_price['List Price'].iloc[0]/estimated_value:.2f} times the estimated value.")
            return result
    except Exception as e:
        print(f"Error generating appraisal report: {e}")
        return

def combine_to_dataframe(comparison_file_ids, manual_data = None, input_file: str = Query(..., description="Input file ID")):
    
    if manual_data is not None:
        try:
            # Convert manual data to the same format as extracted data
            input_property_info = [{
                'Address': manual_data.address,
                'Status': manual_data.status,
                'Subdivision': manual_data.subdivision,
                'Year Built': manual_data.yearBuilt,
                'Living Sq Ft': manual_data.livingSqFt,
                'Total Sq Ft': manual_data.totalSqFt,
                'Bedrooms': manual_data.bedrooms,
                'Bathrooms (Full)': manual_data.bathrooms,
                'Stories': manual_data.stories,
                'Garage Spaces': manual_data.garageSpaces,
                'Private Pool': manual_data.privatePool,
            }]
            
            input_price_info = [{
                'Address': manual_data.address,
                'List Price': manual_data.listPrice,
                'List $/Sq Ft (Living)': manual_data.listPricePerSqFt,
                'Sold Price': manual_data.soldPrice,
                'Sold $/Sq Ft (Living)': manual_data.soldPricePerSqFt,
                'DOM': manual_data.daysOnMarket
            }]
            
            input_features_info = [{
                'Address': manual_data.address,
                'Interior': manual_data.interior,
                'Exterior': manual_data.exterior,
                'Public Remarks': manual_data.publicRemarks
            }]
        except Exception as E:
            print("Error in combining manual data to dataframe", str(E))
            return None
    else:
        try:
                # Get file paths
            input_file_path = uploaded_files[input_file]["file_path"]
            comparison_file_paths = [uploaded_files[fid]["file_path"] for fid in comparison_file_ids]
            
            # Process input file with extract_property_info
            input_property_info, input_price_info, input_features_info, is_rental = extract_property_info(input_file_path)
        except Exception as e:
            print("Error in combining input file to dataframe", str(e))
            return None
    try:
        # Validate comparison files exist
        for file_id in comparison_file_ids:
            if file_id not in uploaded_files or uploaded_files[file_id]["type"] != "comparison":
                raise HTTPException(status_code=404, detail=f"Comparison file {file_id} not found")
        
        # Get comparison file paths
        comparison_file_paths = [uploaded_files[fid]["file_path"] for fid in comparison_file_ids]
        # Result lists
        all_comparison_property_info = []
        all_comparison_price_info = []
        all_comparison_features_info = []
        # Process all comparison files
        for comp_file_path in comparison_file_paths:
            comp_property_info, comp_price_info, comp_features_info, is_rental = extract_property_info(comp_file_path)
            if comp_property_info and comp_price_info:
                all_comparison_property_info.extend(comp_property_info)
                all_comparison_price_info.extend(comp_price_info)
                all_comparison_features_info.extend(comp_features_info)
        # Combine all data
        all_property_info = input_property_info + all_comparison_property_info if input_property_info and all_comparison_property_info else (input_property_info or all_comparison_property_info or [])
        all_price_info = input_price_info + all_comparison_price_info if input_price_info and all_comparison_price_info else (input_price_info or all_comparison_price_info or [])
        all_features_info = input_features_info + all_comparison_features_info if input_features_info and all_comparison_features_info else (input_features_info or all_comparison_features_info or [])
        # Convert to DataFrames
        all_property_info = pd.DataFrame(all_property_info)
        all_price_info = pd.DataFrame(all_price_info)
        all_features_info = pd.DataFrame(all_features_info)
        return all_property_info, all_price_info, all_features_info, is_rental
    except Exception as e:
        print("Error in combining all data into dataframe", str(e))
        return None

# Create FastAPI app instance
app = FastAPI()

app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)
input_file_path = ""
# Global storage for uploaded files (in production, use a database)
uploaded_files = {}
# Create temporary directory for processing
temp_dir = tempfile.mkdtemp(prefix="real_estate_")

# Create reports directory for final outputs only
reports_dir = "reports"
os.makedirs(reports_dir, exist_ok=True)

# Pydantic model for manual input data
class ManualInputData(BaseModel):
    address: str
    status: str
    subdivision: str
    yearBuilt: str
    livingSqFt: str
    totalSqFt: str
    bedrooms: str
    bathrooms: str
    stories: str
    garageSpaces: str
    privatePool: str
    listPrice: str
    listPricePerSqFt: str
    soldPrice: str
    soldPricePerSqFt: str
    daysOnMarket: str
    isRental: bool
    interior: str
    exterior: str
    publicRemarks: str

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint for testing"""
    return {"message": "Real Estate PDF Analysis API is running!"}

@app.post("/upload-input-pdf")
async def upload_input_pdf(file: UploadFile = File(...), token: str = Depends(verify_token)):
    """Upload the main MLS report PDF"""
    try:

        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Generate unique file ID
        file_id = f"input_{uuid.uuid4().hex[:8]}"
        
        # Save file to temporary directory
        file_path = os.path.join(temp_dir, f"{file_id}.pdf")
        global input_file_path
        input_file_path = file_path
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # Store file info
        uploaded_files[file_id] = {
            "filename": file.filename,
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "type": "input"
        }
        
        return {
            "success": True,
            "message": "Input PDF uploaded successfully",
            "file_id": file_id,
            "filename": file.filename,
            "file_size": uploaded_files[file_id]["file_size"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/upload-comparison-pdf")
async def upload_comparison_pdf(files: List[UploadFile] = File(...), token: str = Depends(verify_token)):
    """Upload comparison property PDFs"""
    try:
        uploaded_file_info = []
        for file in files:
            # Validate file type
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF")
            
            # Generate unique file ID
            file_id = f"comp_{uuid.uuid4().hex[:8]}"
            
            # Save file to temporary directory
            file_path = os.path.join(temp_dir, f"{file_id}.pdf")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_property_type = extract_property_type(file_path)
            
            # Store file info
            uploaded_files[file_id] = {
                "filename": file.filename,
                "file_path": file_path,
                "file_size": os.path.getsize(file_path),
                "type": "comparison"
            }
            
            uploaded_file_info.append({
                "file_id": file_id,
                "filename": file.filename,
                "file_size": uploaded_files[file_id]["file_size"]
            })
            global input_file_path
            current_property_type = extract_property_type(input_file_path)
            if temp_property_type != current_property_type:
                try:
                    print("Type mismatch")
                    # Call comparison function to auto fill the data
                    # Think of best way to optimize this as the information is already extracted from the file, save locally it does not have to be run again
                    property_info, price_info, features_info, is_rental = extract_property_info(input_file_path)
                    
                    extracted_data = {}
                    
                    if property_info and len(property_info) > 0:
                        for key, value in property_info[0].items():
                            key = key.replace(" ", "")
                            key  = key.lower()
                            if value is not None:
                                extracted_data[key] = value
                    if features_info and len(features_info) > 0:
                        for key, value in features_info[0].items():
                            key = key.replace(" ", "")
                            key  = key.lower()
                            if value is not None:
                                extracted_data[key] = value
                    return {
                        "success": True,
                        "type_mismatch": True,
                        "message": "Type mismatch, auto filled data",
                        "uploaded_files": uploaded_file_info,
                        "extracted_data": extracted_data   
                    }
                except Exception as e:
                    print(f"Error in type mismatch: {e}")
            
        return {
            "success": True,
            "type_mismatch": False,
            "message": f"{len(uploaded_file_info)} comparison PDF(s) uploaded successfully",
            "uploaded_files": uploaded_file_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
@app.get("/generate-report-chatgpt")
async def generate_report_chatgpt(input_file: str = Query(..., description="Input file ID"), 
                            comparison_files: str = Query(..., description="Comma-separated comparison file IDs"), token: str = Depends(verify_token)):
    """Generate property comparison report"""
    try:
        # Validate input file exists
        if input_file not in uploaded_files or uploaded_files[input_file]["type"] != "input":
            raise HTTPException(status_code=404, detail="Input file not found")
        
        # Parse comparison file IDs
        comparison_file_ids = [fid.strip() for fid in comparison_files.split(",")]
        
        # Combine all data into dataframe
        all_property_info, all_price_info, all_features_info, is_rental = combine_to_dataframe(comparison_file_ids, None, input_file)

        # Generate prompt
        prompt = generate_chatgpt_prompt(all_property_info, all_price_info, all_features_info)

        return {
        "prompt": prompt,
        "message": "Prompt generated successfully",
        "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@app.get("/generate-report")
async def generate_report(input_file: str = Query(..., description="Input file ID"), 
                            comparison_files: str = Query(..., description="Comma-separated comparison file IDs"), token: str = Depends(verify_token)):
    """Generate property comparison report"""
    try:
        # Validate input file exists
        if input_file not in uploaded_files or uploaded_files[input_file]["type"] != "input":
            raise HTTPException(status_code=404, detail="Input file not found")
        
        # Parse comparison file IDs
        comparison_file_ids = [fid.strip() for fid in comparison_files.split(",")]
        
        all_property_info, all_price_info, all_features_info, is_rental = combine_to_dataframe(comparison_file_ids, None, input_file)
        
        # Generate graphs
        generate_graphs(all_price_info, is_rental)
        
        # Generate appraisal report
        input_sq_ft = all_property_info['Living Sq Ft'].iloc[0]
        appraisal_report = generate_appraisal_report(all_price_info, input_sq_ft, is_rental)

        # Create DataFrames
        combined_df = all_property_info
        combined_df_price = all_price_info 
        combined_df_features = all_features_info

        # Here generate prompt for chatgpt and prompt chatgpt api to give response
        # Break down the features to chatgpt5 and everything else to chatgpt4o-mini to minimize costs

        # Styles for PDF report
        styles = getSampleStyleSheet()
        # Generate PDF report in temporary directory
        temp_pdf_path = os.path.join(temp_dir, "property_comparison.pdf")
        doc = SimpleDocTemplate(temp_pdf_path, pagesize=letter, topMargin=30, bottomMargin=30, leftMargin=30, rightMargin=30)

        # Generate styles for cells and table headers
        cell_style = ParagraphStyle(
            name='Cell',
            parent=styles['BodyText'],
            fontName='Times-Roman',
            fontSize=10,
            leading=12,
            spaceAfter=0,
            spaceBefore=0,
            wordWrap='CJK',
            alignment=1
        )
        cell_heading_style = ParagraphStyle(
            name='CellHeading',
            fontName='Times-Bold',
            fontSize=12,
            leading=12,
        )
        # Prepare data for PDF tables
        property_data = [list(combined_df.columns)]
        for index, row in combined_df.iterrows():
            property_data.append([str(cell) if pd.notna(cell) else '' for cell in row])
        
        price_data = [list(combined_df_price.columns)]
        for index, row in combined_df_price.iterrows():
            price_data.append([str(cell) if pd.notna(cell) else '' for cell in row])
        
        # Compute column widths from header text, fit to available width
        def _calc_col_widths(headers, font_name, font_size, available_width):
            padding = 12  # horizontal padding per cell (left+right)
            min_w = 0.6 * inch
            max_w = 2.2 * inch
            raw_widths = []
            for h in headers:
                text = str(h)
                w = stringWidth(text, font_name, font_size) + 2 * padding
                w = max(min_w, min(max_w, w))
                raw_widths.append(w)
            total = sum(raw_widths) or 1.0
            if total > available_width:
                scale = available_width / total
                raw_widths = [max(min_w, w * scale) for w in raw_widths]
            return raw_widths

        header_font = getattr(cell_heading_style, 'fontName', 'Times-Bold')
        header_size = getattr(cell_heading_style, 'fontSize', 12)
        available_width = doc.width
        property_col_widths = _calc_col_widths(property_data[0], header_font, header_size, available_width)
        price_col_widths = _calc_col_widths(price_data[0], header_font, header_size, available_width)

        # Wrap all cell content in Paragraph objects for word wrapping
        for i, row in enumerate(property_data):
            for j, cell in enumerate(row):
                if i == 0:  # Header row
                    property_data[i][j] = Paragraph(str(cell), cell_heading_style)
                else:
                    property_data[i][j] = Paragraph(str(cell), cell_style)
        
        for i, row in enumerate(price_data):
            for j, cell in enumerate(row):
                if i == 0:  # Header row
                    price_data[i][j] = Paragraph(str(cell), cell_heading_style)
                else:
                    price_data[i][j] = Paragraph(str(cell), cell_style)
        
                 # Create tables
        property_table = Table(property_data, colWidths=property_col_widths)
        price_table = Table(price_data, colWidths=price_col_widths)
        
                 # Apply table styles
        property_table.setStyle(TableStyle([
             ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
             ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
             ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
             ('FONTNAME', (0, 0), (-1, 0), 'Times-Roman'),
             ('FONTSIZE', (0, 0), (-1, 0), 9),
             ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
             ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
             ('GRID', (0, 0), (-1, -1), 1, colors.black),
             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
             ('ALIGN', (0, 0), (0, -1), 'LEFT'),
             ('FONTNAME', (0, 1), (0, -1), 'Times-Bold'),
             ('FONTSIZE', (0, 1), (0, -1), 7),
             ('BACKGROUND', (0, 1), (0, -1), colors.lightblue),
             ('ROWBACKGROUNDS', (1, 1), (-1, -1), [colors.beige, colors.white]),
         ]))
        
        price_table.setStyle(TableStyle([
             ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
             ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
             ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
             ('FONTNAME', (0, 0), (-1, 0), 'Times-Roman'),
             ('FONTSIZE', (0, 0), (-1, 0), 9),
             ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
             ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
             ('GRID', (0, 0), (-1, -1), 1, colors.black),
             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
             ('ALIGN', (0, 0), (0, -1), 'LEFT'),
             ('FONTNAME', (0, 1), (0, -1), 'Times-Bold'),
             ('FONTSIZE', (0, 1), (0, -1), 7),
             ('BACKGROUND', (0, 1), (0, -1), colors.lightblue),
             ('ROWBACKGROUNDS', (1, 1), (-1, -1), [colors.beige, colors.white]),
         ]))
        
        # Define styles
        title_style = ParagraphStyle(
            name='Title',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=1
        )
        
        heading_style = ParagraphStyle(
            name='Heading1',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Build PDF story
        story = [
            Paragraph("Property Comparison Analysis", title_style),
            Spacer(1, 20),
            Paragraph("Property Features Comparison", heading_style),
            property_table,
            Spacer(1, 30),
            Paragraph("Price & Market Analysis", heading_style),
            price_table,
            PageBreak(),
            Paragraph("List Price vs Sold Price", heading_style),
        ]
        
        # Add graphs
        try:
            price_chart_path = os.path.join(temp_dir, 'list_price_vs_sold_price.png')
            sqft_chart_path = os.path.join(temp_dir, 'list_price_sqft_vs_sold_price_sqft.png')
            
            if os.path.exists(price_chart_path):
                price_chart = Image(price_chart_path, width=7*inch, height=5*inch)
                story.append(price_chart)
                story.append(Spacer(1, 10))
            
            if os.path.exists(sqft_chart_path):
                story.append(PageBreak())
                story.append(Paragraph("List $/Sq Ft vs Sold $/Sq Ft", heading_style))
                sqft_chart = Image(sqft_chart_path, width=7*inch, height=5*inch)
                story.append(sqft_chart)
        except Exception as e:
            print(f"Error adding graphs to PDF: {e}")
        
        # Add appraisal report
        story.append(PageBreak())
        story.append(Paragraph("Appraisal Report", heading_style))
        story.append(Paragraph("From a comparative market analysis viewpoint:", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        bullet_style = ParagraphStyle(
            name='Bullet',
            parent=styles['BodyText'],
            fontName='Times-Roman',
            fontSize=12,
            leading=12,
            spaceAfter=0,
        )
        for item in appraisal_report:
            story.append(Paragraph(f"• {item}", bullet_style))
            story.append(Spacer(1, 6))
        
        # Build the PDF
        doc.build(story)
        
        # Generate unique report ID
        report_id = f"report_{uuid.uuid4().hex[:8]}"
        
        # Move generated PDF to reports directory (final output)
        report_path = os.path.join(reports_dir, f"{report_id}.pdf")
        shutil.move(temp_pdf_path, report_path)
        
        # Clean up temporary files
        cleanup_temp_files()
        
        # Convert DataFrames to dictionaries for JSON response
        property_comparison = {}
        for col in combined_df.columns:
            # Convert column to dict and replace NaN values with 'N/A'
            col_dict = combined_df[col].to_dict()
            for key, value in col_dict.items():
                if pd.isna(value):
                    col_dict[key] = 'N/A'
            property_comparison[col] = col_dict
        
        price_analysis = {}
        for col in combined_df_price.columns:
            # Convert column to dict and replace NaN values with 'N/A'
            col_dict = combined_df_price[col].to_dict()
            # Replace NaN values with 'N/A'
            for key, value in col_dict.items():
                if pd.isna(value):
                    col_dict[key] = 'N/A'
            price_analysis[col] = col_dict
        
        return {
            "success": True,
            "message": "Report generated successfully",
            "report_data": {
                "property_comparison": property_comparison,
                "price_analysis": price_analysis,
                "appraisal_report": appraisal_report
            },
            "report_id": report_id,
            "report_url": f"/download-report/{report_id}",
            "graphs_generated": [
                "list_price_vs_sold_price.png",
                "list_price_sqft_vs_sold_price_sqft.png"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@app.post("/generate-chatgpt-prompt-manual")
async def generate_chatgpt_prompt_manual(manual_data: ManualInputData, comparison_files: str = Query(..., description="Comma-separated comparison file IDs"), token: str = Depends(verify_token)):
    try:
        # Parse comparison file IDs
        comparison_file_ids = [fid.strip() for fid in comparison_files.split(",")]
        
        all_property_info, all_price_info, all_features_info, is_rental = combine_to_dataframe(comparison_file_ids, manual_data, None)
        prompt = generate_chatgpt_prompt(all_property_info, all_price_info, all_features_info)
        return {
            "success": True,
            "message": "Prompt generated successfully",
            "prompt": prompt
        }

    except Exception as e:
        print("Error in generating manual chatgpt prompt", str(e))

# HANDLE MANUAL INPUT
@app.post("/generate-report-manual")
async def generate_report_manual(manual_data: ManualInputData, comparison_files: str = Query(..., description="Comma-separated comparison file IDs"), token: str = Depends(verify_token)):
    """Generate property comparison report with manual input data"""
    try:
        # Parse comparison file IDs
        comparison_file_ids = [fid.strip() for fid in comparison_files.split(",")]
        
        all_property_info, all_price_info, all_features_info, is_rental = combine_to_dataframe(comparison_file_ids, manual_data=manual_data, input_file=None)
        
        
        generate_graphs(all_price_info, manual_data.isRental)
        
        # Create DataFrames
        combined_df = all_property_info
        combined_df_price = all_price_info
        combined_df_features = all_features_info    
        # Generate appraisal report - use the manual input rental status
        input_sq_ft = all_property_info['Living Sq Ft'].iloc[0]
        appraisal_report = generate_appraisal_report(all_price_info, input_sq_ft, manual_data.isRental)
        
        # Styles for PDF report
        styles = getSampleStyleSheet()
        # Generate PDF report in temporary directory
        temp_pdf_path = os.path.join(temp_dir, "property_comparison.pdf")
        doc = SimpleDocTemplate(temp_pdf_path, pagesize=letter, topMargin=30, bottomMargin=30, leftMargin=30, rightMargin=30)

        # Generate styles for cells and table headers
        cell_style = ParagraphStyle(
            name='Cell',
            parent=styles['BodyText'],
            fontName='Times-Roman',
            fontSize=10,
            leading=12,
            spaceAfter=0,
            spaceBefore=0,
            wordWrap='CJK',
            alignment=1
        )
        cell_heading_style = ParagraphStyle(
            name='CellHeading',
            fontName='Times-Bold',
            fontSize=12,
            leading=12,
        )
        property_data = [list(combined_df.columns)]
        for index, row in combined_df.iterrows():
            property_data.append([str(cell) if pd.notna(cell) else '' for cell in row])
        
        price_data = [list(combined_df_price.columns)]
        for index, row in combined_df_price.iterrows():
            price_data.append([str(cell) if pd.notna(cell) else '' for cell in row])
        
        # Compute column widths from header text, fit to available width
        def _calc_col_widths(headers, font_name, font_size, available_width):
            padding = 12  # horizontal padding per cell (left+right)
            min_w = 0.6 * inch
            max_w = 2.2 * inch
            raw_widths = []
            for h in headers:
                text = str(h)
                w = stringWidth(text, font_name, font_size) + 2 * padding
                w = max(min_w, min(max_w, w))
                raw_widths.append(w)
            total = sum(raw_widths) or 1.0
            if total > available_width:
                scale = available_width / total
                raw_widths = [max(min_w, w * scale) for w in raw_widths]
            return raw_widths

        header_font = getattr(cell_heading_style, 'fontName', 'Times-Bold')
        header_size = getattr(cell_heading_style, 'fontSize', 12)
        available_width = doc.width
        property_col_widths = _calc_col_widths(property_data[0], header_font, header_size, available_width)
        price_col_widths = _calc_col_widths(price_data[0], header_font, header_size, available_width)

        # Wrap all cell content in Paragraph objects for word wrapping
        for i, row in enumerate(property_data):
            for j, cell in enumerate(row):
                if i == 0:  # Header row
                    property_data[i][j] = Paragraph(str(cell), cell_heading_style)
                else:
                    property_data[i][j] = Paragraph(str(cell), cell_style)
        
        for i, row in enumerate(price_data):
            for j, cell in enumerate(row):
                if i == 0:  # Header row
                    price_data[i][j] = Paragraph(str(cell), cell_heading_style)
                else:
                    price_data[i][j] = Paragraph(str(cell), cell_style)
        
                 # Create tables
        property_table = Table(property_data, colWidths=property_col_widths)
        price_table = Table(price_data, colWidths=price_col_widths)
        # Apply table styles
        property_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (0, -1), 'Times-Bold'),
            ('FONTSIZE', (0, 1), (0, -1), 7),
            ('BACKGROUND', (0, 1), (0, -1), colors.lightblue),
            ('ROWBACKGROUNDS', (1, 1), (-1, -1), [colors.beige, colors.white]),
        ]))
        
        price_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (0, -1), 'Times-Bold'),
            ('FONTSIZE', (0, 1), (0, -1), 7),
            ('BACKGROUND', (0, 1), (0, -1), colors.lightblue),
            ('ROWBACKGROUNDS', (1, 1), (-1, -1), [colors.beige, colors.white]),
        ]))
        
        # Define styles
        title_style = ParagraphStyle(
            name='Title',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=1
        )
        
        heading_style = ParagraphStyle(
            name='Heading1',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Build PDF story
        story = [
            Paragraph("Property Comparison Analysis", title_style),
            Spacer(1, 20),
            Paragraph("Property Features Comparison", heading_style),
            property_table,
            Spacer(1, 30),
            Paragraph("Price & Market Analysis", heading_style),
            price_table,
            PageBreak(),
            Paragraph("List Price vs Sold Price", heading_style),
        ]
        
        # Add graphs
        try:
            price_chart_path = os.path.join(temp_dir, 'list_price_vs_sold_price.png')
            sqft_chart_path = os.path.join(temp_dir, 'list_price_sqft_vs_sold_price_sqft.png')
            
            if os.path.exists(price_chart_path):
                price_chart = Image(price_chart_path, width=7*inch, height=5*inch)
                story.append(price_chart)
                story.append(Spacer(1, 10))
            
            if os.path.exists(sqft_chart_path):
                story.append(PageBreak())
                story.append(Paragraph("List $/Sq Ft vs Sold $/Sq Ft", heading_style))
                sqft_chart = Image(sqft_chart_path, width=7*inch, height=5*inch)
                story.append(sqft_chart)
        except Exception as e:
            print(f"Error adding graphs to PDF: {e}")
        
        # Add appraisal report
        story.append(PageBreak())
        story.append(Paragraph("Appraisal Report", heading_style))
        story.append(Paragraph("From a comparative market analysis viewpoint:", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        bullet_style = ParagraphStyle(
            name='Bullet',
            parent=styles['BodyText'],
            fontName='Times-Roman',
            fontSize=12,
            leading=12,
            spaceAfter=0,
        )
        for item in appraisal_report:
            story.append(Paragraph(f"• {item}", bullet_style))
            story.append(Spacer(1, 6))
        
        # Build the PDF
        doc.build(story)
        
        # Generate unique report ID
        report_id = f"report_{uuid.uuid4().hex[:8]}"
        
        # Move generated PDF to reports directory (final output)
        report_path = os.path.join(reports_dir, f"{report_id}.pdf")
        shutil.move(temp_pdf_path, report_path)
        
        # Clean up temporary files
        cleanup_temp_files()
        
        property_comparison = {}
        for col in combined_df.columns:
            # Convert column to dict and replace NaN values with 'N/A'
            col_dict = combined_df[col].to_dict()
            for key, value in col_dict.items():
                if pd.isna(value):
                    col_dict[key] = 'N/A'
            property_comparison[col] = col_dict
        
        price_analysis = {}
        for col in combined_df_price.columns:
            # Convert column to dict and replace NaN values with 'N/A'
            col_dict = combined_df_price[col].to_dict()
            # Replace NaN values with 'N/A'
            for key, value in col_dict.items():
                if pd.isna(value):
                    col_dict[key] = 'N/A'
            price_analysis[col] = col_dict
        return {
            "success": True,
            "message": "Report generated successfully",
            "report_data": {
                "property_comparison": property_comparison,
                "price_analysis": price_analysis,
                "appraisal_report": appraisal_report
            },
            "report_id": report_id,
            "report_url": f"/download-report/{report_id}",
            "graphs_generated": [
                "list_price_vs_sold_price.png",
                "list_price_sqft_vs_sold_price_sqft.png"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@app.get("/download-report/{report_id}")
async def download_report(report_id: str, token: str = Depends(verify_token)):
    """Download the generated PDF report"""
    try:
        report_path = os.path.join("reports", f"{report_id}.pdf")
        
        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Report not found")
        
        return FileResponse(
            path=report_path,
            filename=f"property_comparison_{report_id}.pdf",
            media_type="application/pdf"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.get("/view-report/{report_id}")
async def view_report(report_id: str, token: str = Depends(verify_token_query)):
    """View the generated PDF report in browser"""
    try:
        report_path = os.path.join("reports", f"{report_id}.pdf")
        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Report not found")
        
        return FileResponse(
            path=report_path,
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"View failed: {str(e)}")

@app.get("/files")
async def list_uploaded_files(token: str = Depends(verify_token)):
    """List all uploaded files (for debugging)"""
    return {
        "uploaded_files": uploaded_files
    }

@app.delete("/files/{file_id}")
async def delete_file(file_id: str, token: str = Depends(verify_token)):
    """Delete an uploaded file"""
    try:
        if file_id not in uploaded_files:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_info = uploaded_files[file_id]
        if os.path.exists(file_info["file_path"]):
            os.remove(file_info["file_path"])
        del uploaded_files[file_id]
        
        return {
            "success": True,
            "message": f"File {file_id} deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

def cleanup_on_shutdown():
    """Clean up temporary directory on server shutdown"""
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Error cleaning up temporary directory: {e}")

# %%
if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    finally:
        cleanup_on_shutdown()
