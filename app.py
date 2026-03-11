from flask import Flask, jsonify, render_template, request, flash, redirect, url_for, session
import json
import jwt
import sqlalchemy
import os
import pandas as pd
from pandasql import sqldf
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')
app.config['TEMPLATES_AUTO_RELOAD'] = True


@app.route('/', methods=['GET', 'POST'])
def home():
    sheet_names = session.get('sheet_names', [])#!Whats this
    columns = session.get('columns', [])
    query = ""
    excel_rows = []
    excel_cols = []
    file_path = session.get('uploaded_file')

    if request.method == 'POST':
        file = request.files.get("file")
        button = request.form.get('button')
        if file and not button:
            if file.filename.endswith(('.xlsx', '.xls')):#!, '.xls'
                try:
                    # ?saving to disk
                    upload_dir = "uploads"
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, "temp.xlsx")
                    file.save(file_path)

                    session['uploaded_file'] = file_path
                    session['filename'] = file.filename

                    df = {}

                    # !Used to be file_path
                    df = pd.read_excel(file_path, sheet_name=None)
                    sheet_names = list(df.keys())
                    session['sheet_names'] = sheet_names
                    session['sheet_count'] = len(sheet_names)
                    
                    first_sheet = sheet_names[0]
                    columns = df[first_sheet].columns.tolist()
                    session['columns'] = columns
                except Exception as e:
                    flash(f"File has to be an Excel file: {e}", "error")
                    print(e)
                    return render_template('file.html', query=query, sheet_names=sheet_names)
                
                return redirect(url_for('home'))

        elif button == 'reset_btn':
            session.clear()
            return redirect(url_for('home'))
            
        elif button == 'run_btn':
            try:
                file_path = session.get('uploaded_file')
                if not file_path:
                    flash("No file uploaded", "error")
                    return redirect(url_for('home'))
                
                selected_col = request.form.getlist('columns[]')
                selected_col = [c for c in selected_col if c.strip()]

                user_sheet = request.form.get('sheet')
                where = request.form.getlist('where_clause[]')
                order_by = request.form.get('order_by')
                group_by = request.form.get('group_by')
                dire = request.form.get('direction')
                operators = request.form.getlist('operator[]')
                
                df = pd.read_excel(file_path, sheet_name=None)
                sheet_names = list(df.keys())
                
                if not selected_col or selected_col[0] == "":
                    cols = "*"
                else:
                    cols = ", ".join(f'"{c}"' for c in selected_col)

                query = f"SELECT {cols}"
                
                if user_sheet and user_sheet in df:
                    env = {user_sheet: df[user_sheet]}
                    query += f" FROM {user_sheet}"
                else:
                    default = sheet_names[0]
                    env = {default: df[default]}
                    query += f" FROM {default}"

                clean_where = [w.strip() for w in where if w.strip()]
                if clean_where:
                    query += " WHERE " + clean_where[0]
                    for i in range(1, len(clean_where)):
                        if i-1 < len(operators):
                            op = operators[i-1]
                        else:
                            op = "AND"
                        query += f" {op} {clean_where[i]}"

                if group_by:
                    query += f" GROUP BY {group_by}"

                if order_by:
                    query += f" ORDER BY {order_by}"
                else:
                    order_by = None

                if dire and order_by:
                    query += f" {dire}"
                    
                excel_query = sqldf(query, env)  # !locals()
                excel_rows = excel_query.values.tolist()
                excel_cols = excel_query.columns.tolist()

                print("Running query:", query)
                return render_template('file.html', query=query, sheet_names=sheet_names, columns=columns, excel_rows=excel_rows, excel_cols=excel_cols)
                
            except UnboundLocalError:
                flash("Error with input", "error")
                return render_template('file.html', query=query, sheet_names=sheet_names, columns=columns, excel_rows=excel_rows, excel_cols=excel_cols)
            except Exception as e:
                flash(f"Error: {e}", "error")
                print(e)
                return render_template('file.html', query=query, sheet_names=sheet_names, columns=columns, excel_rows=excel_rows, excel_cols=excel_cols)
        else:
            flash("Error", "error")
            return render_template('file.html', query=query, sheet_names=sheet_names, columns=columns, excel_rows=excel_rows, excel_cols=excel_cols)

    return render_template('file.html',  sheet_names=sheet_names, columns=columns)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)