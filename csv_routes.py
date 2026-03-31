from flask import Blueprint, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
from models import db, AccountBook, Income, Expense
from datetime import datetime
import pandas as pd
from io import StringIO, BytesIO
import zipfile


csv_bp = Blueprint('csv', __name__)


@csv_bp.route('/export_multiple', methods=['POST'])
@login_required
def export_multiple():
    try:
        selected_book_ids = request.form.getlist('book_ids')
        export_format = request.form.get('export_format', 'single')  # 'single' or 'separate'
        
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
                'Date': inc.date.strftime('%Y-%m-%d'),
                'Type': 'Income',
                'Category': inc.category,
                'Description': inc.description,
                'Amount': inc.amount
            })
        
        for exp in expenses:
            all_transactions.append({
                'Account Book': book.bookname,
                'Date': exp.date.strftime('%Y-%m-%d'),
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
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for book in books:
            # collect current account book transaction
            transactions = []
            
            incomes = Income.query.filter_by(account_book_id=book.id).all()
            expenses = Expense.query.filter_by(account_book_id=book.id).all()
            
            for inc in incomes:
                transactions.append({
                    'Date': inc.date.strftime('%Y-%m-%d'),
                    'Type': 'Income',
                    'Category': inc.category,
                    'Description': inc.description,
                    'Amount': inc.amount
                })
            
            for exp in expenses:
                transactions.append({
                    'Date': exp.date.strftime('%Y-%m-%d'),
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