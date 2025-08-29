# API Endpoints 
from fastapi import FastAPI, Query, Depends, HTTPException
from pdf_handle import generate_chatgpt_prompt, combine_to_dataframe
from schemas.manual_input import ManualInputData
from core.dependencies import get_file_storage_service
from schemas.file_storage_service import FileStorageService
from fastapi.middleware.cors import CORSMiddleware
from middleware import verify_token, verify_token_query
from services.report_service import generate_graphs, generate_appraisal_report, generate_chatgpt_prompt, combine_to_dataframe
from services.llm_service import generate_chatgpt_prompt_features, get_feature_list, generate_chatgpt_prompt_mini
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.platypus import Image, PageBreak
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import pandas as pd
import os
import uuid
import shutil
from fastapi.responses import FileResponse
from fastapi import APIRouter

app = APIRouter()


@app.get("/generate-report-chatgpt")
async def generate_report_chatgpt(token: str = Depends(verify_token), 
                            file_storage_service: FileStorageService = Depends(get_file_storage_service)):
    """Generate property comparison report"""
    try:
        
        
        # Combine all data into dataframe
        all_property_info, all_price_info, all_features_info, is_rental = combine_to_dataframe(file_storage_service, None)

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
async def generate_report(token: str = Depends(verify_token), file_storage_service: FileStorageService = Depends(get_file_storage_service)):
    """Generate property comparison report"""
    try:
        # Validate input file exists
        
        all_property_info, all_price_info, all_features_info, is_rental = combine_to_dataframe(file_storage_service, None)
        
        # Generate graphs
        generate_graphs(all_price_info, is_rental, file_storage_service.temp_dir)
        
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
        temp_pdf_path = os.path.join(file_storage_service.temp_dir, "property_comparison.pdf")
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
            price_chart_path = os.path.join(file_storage_service.temp_dir, 'list_price_vs_sold_price.png')
            sqft_chart_path = os.path.join(file_storage_service.temp_dir, 'list_price_sqft_vs_sold_price_sqft.png')
            
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
        report_path = os.path.join("reports", f"{report_id}.pdf")
        shutil.move(temp_pdf_path, report_path)
        
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
async def generate_chatgpt_prompt_manual(manual_data: ManualInputData, token: str = Depends(verify_token), file_storage_service: FileStorageService = Depends(get_file_storage_service)):
        # Parse comparison file IDs
        
    try:
        all_property_info, all_price_info, all_features_info, is_rental = combine_to_dataframe(file_storage_service, manual_data=manual_data)
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
async def generate_report_manual(manual_data: ManualInputData, comparison_files: str = Query(..., description="Comma-separated comparison file IDs"), token: str = Depends(verify_token), file_storage_service: FileStorageService = Depends(get_file_storage_service)):
    """Generate property comparison report with manual input data"""
    try:
        # Parse comparison file IDs
        comparison_file_ids = [fid.strip() for fid in comparison_files.split(",")]
        
        all_property_info, all_price_info, all_features_info, is_rental = combine_to_dataframe(file_storage_service, manual_data=manual_data)
        
        
        generate_graphs(all_price_info, manual_data.isRental, file_storage_service.temp_dir)
        
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
        temp_pdf_path = os.path.join(file_storage_service.temp_dir, "property_comparison.pdf")
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
            price_chart_path = os.path.join(file_storage_service.temp_dir, 'list_price_vs_sold_price.png')
            sqft_chart_path = os.path.join(file_storage_service.temp_dir, 'list_price_sqft_vs_sold_price_sqft.png')
            
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
        report_path = os.path.join("reports", f"{report_id}.pdf")
        shutil.move(temp_pdf_path, report_path)
        
        
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


@app.delete("/files/{file_id}")
async def delete_file(file_id: str, token: str = Depends(verify_token), file_storage_service: FileStorageService = Depends(get_file_storage_service)):
    """Delete an uploaded file"""
    try:
        input_file_name = "input_" + file_id
        for file in file_storage_service.input_files:
            if file.filename == input_file_name:
                file_storage_service.input_files.remove(file)
                os.remove(file.file_path)
                return {
                    "success": True,
                    "message": f"File {file_id} deleted successfully"
                }
        
        comparison_file_name = "comp_" + file_id

        for file in file_storage_service.comparison_files:
            if file.filename == comparison_file_name:
                file_storage_service.comparison_files.remove(file)
                os.remove(file.file_path)
                return {
                    "success": True,
                    "message": f"File {file_id} deleted successfully"
                }
        raise HTTPException(status_code=404, detail="File not found")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
__all__ = ["app"]