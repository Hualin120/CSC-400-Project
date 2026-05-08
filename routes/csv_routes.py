from flask import Blueprint, redirect, url_for, flash, request, make_response, session
from flask_login import login_required, current_user
from models import db, AccountBook, Income, Expense
from datetime import datetime
import pandas as pd
from io import StringIO, BytesIO, TextIOWrapper
import zipfile

csv_bp = Blueprint('csv', __name__)

ALLOWED_CATEGORIES = {
    'income': ['Salary', 'Part Time', 'Freelance', 'Allowance', 'Refund', 'Gift', 'Other'],
    'expense': ['Housing', 'Utilities', 'Groceries', 'Food', 'Transportation', 'Insurance', 'Subscriptions', 'Entertainment', 'Shopping', 'Medical', 'Travel', 'Other']
}

# standardize column name Format: first letter capitalized, rest lowercase
def format_column_name(col):
    col = col.strip()
    if not col:
        return col
    
    if len(col) > 1:
        return col[0].upper() + col[1:].lower()
    
    return col.upper()

def format_category(cat_str):

    # format category names: capitalize the first letter; the rest are lowercase
    cat_str = cat_str.strip()
    if not cat_str:
        return cat_str
    
    words = cat_str.split()
    
    formatted_words = []
    for word in words:
        if len(word) > 1:
            formatted_words.append(word[0].upper() + word[1:].lower())
        elif len(word) == 1:
            formatted_words.append(word.upper())
        else:
            formatted_words.append(word)
    
    return ' '.join(formatted_words)

def validate_and_create_transaction(row, current_book_id):
    # verify type
    transaction_type = str(row['Type']).lower().strip()
    if transaction_type not in ['income', 'expense']:
        raise ValueError(f"Invalid type '{row['type']}'. Must be 'Income' or 'Expense'. ")

    # Parse Date
    date_str = str(row['Date']).strip()
    parsed = False

    # verify if the date is digit or letter?
    if not any(c.isdigit() for c in date_str):
        raise ValueError(f"Date '{date_str}' contains no numbers. Please enter a valid date. ")

    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m-%d-%Y', '%m/%d/%Y']:
        try:
            date = datetime.strptime(date_str, fmt)
            parsed = True
            break
        except ValueError:
            continue

    if not parsed:
        raise ValueError(f"Invalid date format '{date_str}'. Use MM-DD-YYYY. ")
    
    # date time cannot be later than the current time
    today = datetime.now().date()
    if date.date() > today:
        raise ValueError(f"Date '{date_str}' cannot be in the future. ")
    
    # verify amount
    try:
        amount = float(row['Amount'])
        if amount <= 0:
            raise ValueError(f"Amount must be greater than 0.")
    except:
        raise ValueError(f"Invalid amount '{row['Amount']}'. Please enter a positive number. ")
    
    # verify category 
    # make all category type to be: first character capital, rest lowercase
    category = format_category(str(row['Category']))
    if not category:
        raise ValueError(f"Category cannot be empty. ")
    
    # check if the category is in the allowed list
    allowed = ALLOWED_CATEGORIES[transaction_type]
    if category not in allowed:
        allowed_str = ', '.join(allowed)
        raise ValueError(f"Category '{category}' is not valid for {transaction_type}. Allowed: {allowed_str}. ")

    # verify description
    description = str(row['Description']).strip()
    if not description:
        raise ValueError(f"Description cannot be empty. ")
    
    # create transaction
    if transaction_type == 'income':
        return Income(
            description=description[:120],
            category=category[:50],
            amount=amount,
            date=date,
            account_book_id=current_book_id
        )

    else:
        return Expense(
            description=description[:120],
            category=category[:50],
            amount=amount,
            date=date,
            account_book_id=current_book_id
        )

@csv_bp.route('/import', methods=['POST'])
@login_required
def import_csv():
    try:
        # to check whether a file is upload
        if 'csv_file' not in request.files:
            flash('No file selected. ', 'danger')
            return redirect(url_for('transactions'))
        
        file = request.files['csv_file']

        if file.filename == '':
            flash('No file selected. ', 'danger')
            return redirect(url_for('transactions'))
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file. ', 'danger')
            return redirect(url_for('transactions'))
        
        # getting current account book
        current_book_id = session.get('current_account_book')
        if not current_book_id:
            flash('Please select an account book first. ', 'danger')
            return redirect(url_for('transactions'))
        
        # verify current account book is belong current user
        current_book = AccountBook.query.filter_by(
            id=current_book_id, 
            user_id=current_user.id
        ).first()
        
        if not current_book:
            flash('Invalid account book selected. ', 'danger')
            return redirect(url_for('transactions'))   
        
        # read CSV file, useing TextIOWrapper
        stream = TextIOWrapper(file.stream, encoding='utf-8-sig')
        df = pd.read_csv(stream)
        
        # verify colums
        df.columns = [format_column_name(col) for col in df.columns]

        required_columns = ['Date', 'Type', 'Category', 'Description', 'Amount']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            flash(f'CSV is missing required columns: {", ".join(missing_columns)}. ', 'danger')
            return redirect(url_for('transactions'))

        # import data and verify the format of the CSV file
        valid_transactions = []
        errors = []
        
        for index, row in df.iterrows():
            try:
                # call def validate_and create_transaction to verify ^^^^^
                transaction = validate_and_create_transaction(row, current_book_id)
                valid_transactions.append(transaction)
                
            except Exception as e:
                errors.append(f"Row {index+2}: {str(e)}")
        
        if errors:
            # only should the first 5 error message
            error_msg = f'Import cancelled. Found {len(errors)} error(s):\n'
            error_msg += '\n'.join(errors[:5])
            if len(errors) > 5:
                error_msg += f'\n... and {len(errors)-5} more errors. '
            flash(error_msg, 'danger')
            return redirect(url_for('transactions'))
        
        for transaction in valid_transactions:
            db.session.add(transaction)
        
        db.session.commit()
        
        flash(f'Successfully imported {len(valid_transactions)} transactions into "{current_book.bookname}". ', 'success')
        return redirect(url_for('transactions'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error importing CSV: {str(e)}', 'danger')
        return redirect(url_for('transactions'))
    
@csv_bp.route('/template')
@login_required
def download_template():
    # download CSV template
    template_data = [
        {'Date': '03/31/2026', 'Type': 'Income', 'Category': 'Salary', 'Description': 'Monthly salary', 'Amount': 851.67},
        {'Date': '03/30/2026', 'Type': 'Expense', 'Category': 'Food', 'Description': 'Lunch', 'Amount': 15.50},
        {'Date': '04/01/2026', 'Type': 'Expense', 'Category': 'Shopping', 'Description': 'Groceries', 'Amount': 45.30},
    ]
    
    df = pd.DataFrame(template_data)
    output = StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=csv_template.csv'
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    
    return response

@csv_bp.route('/export_multiple', methods=['POST'])
@login_required
def export_multiple():
    try:
        selected_book_ids = request.form.getlist('book_ids')
        export_format = request.form.get('export_format', 'single')
        
        if not selected_book_ids:
            flash('Please select at least one account book.', 'danger')
            return redirect(url_for('transactions'))
        
        # verify account books are all belong to current user
        books = AccountBook.query.filter(
            AccountBook.id.in_(selected_book_ids),
            AccountBook.user_id == current_user.id
        ).all()
        
        if not books:
            flash('No valid account books selected.', 'danger')
            return redirect(url_for('transactions'))
        
        # base on the process method to export format
        if export_format == 'single':
            return export_as_single_csv(books)
        else:
            return export_as_zip(books)
        
    except Exception as e:
        flash(f'Error exporting: {str(e)}', 'danger')
        return redirect(url_for('transactions'))

def export_as_single_csv(books):
    all_transactions = []
    
    for book in books:
        incomes = Income.query.filter_by(account_book_id=book.id).all()
        expenses = Expense.query.filter_by(account_book_id=book.id).all()
        
        for inc in incomes:
            all_transactions.append({
                'Account Book': book.bookname,
                'Date': inc.date.strftime('%m/%d/%Y'),
                'Type': 'Income',
                'Category': inc.category,
                'Description': inc.description,
                'Amount': inc.amount
            })
        
        for exp in expenses:
            all_transactions.append({
                'Account Book': book.bookname,
                'Date': exp.date.strftime('%m/%d/%Y'),
                'Type': 'Expense',
                'Category': exp.category,
                'Description': exp.description,
                'Amount': exp.amount
            })
    
    if not all_transactions:
        flash('No transactions found in selected account books.', 'warning')
        return redirect(url_for('transactions'))
    
    # sort by Date
    all_transactions.sort(key=lambda x: x['Date'], reverse=True)
    
    # create dataFrame
    df = pd.DataFrame(all_transactions)
    
    # add summary information
    output = StringIO()
    
    # write transaction data
    output.write("=== TRANSACTIONS ===\n")
    df.to_csv(output, index=False, encoding='utf-8-sig')
    
    # write summary to each account book
    output.write("\n=== SUMMARY BY ACCOUNT BOOK ===\n")
    summary = []
    for book in books:
        book_transactions = [t for t in all_transactions if t['Account Book'] == book.bookname]
        book_income = sum([t['Amount'] for t in book_transactions if t['Type'] == 'Income'])
        book_expense = sum([t['Amount'] for t in book_transactions if t['Type'] == 'Expense'])
        summary.append({
            'Account Book': book.bookname,
            'Total Income': book_income,
            'Total Expense': book_expense,
            'Balance': book_income - book_expense,
            'Transaction Count': len(book_transactions)
        })
    
    df_summary = pd.DataFrame(summary)
    df_summary.to_csv(output, index=False, encoding='utf-8-sig')
    
    # write overall summary
    total_income = sum([t['Amount'] for t in all_transactions if t['Type'] == 'Income'])
    total_expense = sum([t['Amount'] for t in all_transactions if t['Type'] == 'Expense'])
    output.write(f"\n=== OVERALL SUMMARY ===\n")
    output.write(f"Total Income,{total_income}\n")
    output.write(f"Total Expense,{total_expense}\n")
    output.write(f"Net Balance,{total_income - total_expense}\n")
    output.write(f"Total Transactions,{len(all_transactions)}\n")
    output.write(f"Account Books,{len(books)}\n")
    
    output.seek(0)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"export_{len(books)}_books_combined_{timestamp}.csv"
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    
    flash(f'Exported {len(all_transactions)} transactions from {len(books)} account books (combined file).', 'success')
    return response

def export_as_zip(books):
    zip_buffer = BytesIO()
    exported_count = 0
    
    # create a zip file
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for book in books:
            # collect current account book transaction
            transactions = []
            
            incomes = Income.query.filter_by(account_book_id=book.id).all()
            expenses = Expense.query.filter_by(account_book_id=book.id).all()
            
            # convert income/expense records to dictionary format
            for inc in incomes:
                transactions.append({
                    'Date': inc.date.strftime('%m/%d/%Y'),
                    'Type': 'Income',
                    'Category': inc.category,
                    'Description': inc.description,
                    'Amount': inc.amount
                })
            
            for exp in expenses:
                transactions.append({
                    'Date': exp.date.strftime('%m/%d/%Y'),
                    'Type': 'Expense',
                    'Category': exp.category,
                    'Description': exp.description,
                    'Amount': exp.amount
                })
            
            if transactions:
                transactions.sort(key=lambda x: x['Date'], reverse=True)
                df = pd.DataFrame(transactions)
                
                # add account book summary to file content
                csv_buffer = StringIO()
                
                # write transacation infomation
                df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                
                # write overall summary 
                book_income = sum([t['Amount'] for t in transactions if t['Type'] == 'Income'])
                book_expense = sum([t['Amount'] for t in transactions if t['Type'] == 'Expense'])
                csv_buffer.write(f"\n=== SUMMARY ===\n")
                csv_buffer.write(f"Total Income,{book_income}\n")
                csv_buffer.write(f"Total Expense,{book_expense}\n")
                csv_buffer.write(f"Balance,{book_income - book_expense}\n")
                csv_buffer.write(f"Transaction Count,{len(transactions)}\n")
                
                csv_buffer.seek(0)
                
                # Remove special characters from filenames.
                safe_name = "".join(c for c in book.bookname if c.isalnum() or c in (' ', '-', '_')).strip()
                filename = f"{safe_name}_transactions.csv"
                zip_file.writestr(filename, csv_buffer.getvalue())
                exported_count += 1
    
    if exported_count == 0:
        flash('No transactions found in selected account books.', 'warning')
        return redirect(url_for('transactions'))
    
    zip_buffer.seek(0)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"export_{exported_count}_books_{timestamp}.zip"
    
    response = make_response(zip_buffer.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'application/zip'
    
    flash(f'Exported {exported_count} account books as separate CSV files in ZIP archive.', 'success')
    return response