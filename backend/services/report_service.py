import pandas as pd
import re
import PyPDF2
from schemas.file_storage_service import FileStorageService
from core.dependencies import get_file_storage_service
import os
import matplotlib.pyplot as plt

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

def extract_property_type(file_path):
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if 'residential customer report' in text.lower():
                return "Residential"
            else:
                return "Rental"

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

def combine_to_dataframe(file_storage_service, manual_data = None):
    
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
            input_file_path = file_storage_service.input_files[0].file_path
            comparison_file_paths = [file_storage_service.comparison_files[i].file_path for i in range(len(file_storage_service.comparison_files))]
            
            # Process input file with extract_property_info
            input_property_info, input_price_info, input_features_info, is_rental = extract_property_info(input_file_path)
        except Exception as e:
            print("Error in combining input file to dataframe", str(e))
            return None
    try:
        # Validate comparison files exist
        
        comparison_file_paths = [file_storage_service.comparison_files[i].file_path for i in range(len(file_storage_service.comparison_files))]
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

def generate_graphs(combined_df_price, is_rental, temp_dir):
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
