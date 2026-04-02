from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'blood-organ-donation-hub-secret-key-2024'

DATABASE = 'donation_hub.db'

# Blood groups and organs for dropdowns
BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
ORGANS = ['Blood Only', 'Kidney', 'Liver', 'Heart', 'Lungs', 'Pancreas', 'Eyes', 'Bone Marrow', 'All Organs']
GENDERS = ['Male', 'Female', 'Other']


def get_db_connection():
    conn = sqlite3.connect(DATABASE, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS donors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                blood_group TEXT NOT NULL,
                organ TEXT NOT NULL,
                location TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Create indexes for efficient searching
        conn.execute('CREATE INDEX IF NOT EXISTS idx_blood_group ON donors(blood_group)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_organ ON donors(organ)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_location ON donors(location)')
        
        # Insert sample data
        sample_donors = [
            ('John Smith', 28, 'Male', 'john.smith@email.com', 'O+', 'Blood Only', 'New York', '555-0101'),
            ('Sarah Johnson', 34, 'Female', 'sarah.j@email.com', 'A+', 'Kidney', 'Los Angeles', '555-0102'),
            ('Michael Chen', 25, 'Male', 'michael.chen@email.com', 'B-', 'Eyes', 'Chicago', '555-0103'),
            ('Emily Davis', 30, 'Female', 'emily.davis@email.com', 'AB+', 'All Organs', 'Houston', '555-0104'),
            ('Robert Wilson', 42, 'Male', 'robert.w@email.com', 'O-', 'Blood Only', 'Phoenix', '555-0105'),
            ('Lisa Anderson', 29, 'Female', 'lisa.a@email.com', 'A-', 'Bone Marrow', 'Philadelphia', '555-0106'),
            ('David Brown', 35, 'Male', 'david.brown@email.com', 'B+', 'Liver', 'San Antonio', '555-0107'),
            ('Jennifer Lee', 27, 'Female', 'jennifer.lee@email.com', 'O+', 'Blood Only', 'San Diego', '555-0108'),
        ]
        
        conn.executemany('''
            INSERT INTO donors (name, age, gender, email, blood_group, organ, location, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_donors)
        
        conn.commit()
        conn.close()
        print("Database initialized with sample data.")


@app.route('/')
def index():
    conn = get_db_connection()
    donor_count = conn.execute('SELECT COUNT(*) as count FROM donors').fetchone()['count']
    conn.close()
    return render_template('index.html', donor_count=donor_count)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '').strip()
        email = request.form.get('email', '').strip()
        blood_group = request.form.get('blood_group', '').strip()
        organ = request.form.get('organ', '').strip()
        location = request.form.get('location', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Validation
        errors = []
        if not name:
            errors.append('Name is required')
        if not age or not age.isdigit() or int(age) < 18 or int(age) > 65:
            errors.append('Age must be between 18 and 65')
        if not gender:
            errors.append('Gender is required')
        if not email or '@' not in email:
            errors.append('Valid email is required')
        if not blood_group:
            errors.append('Blood group is required')
        if not organ:
            errors.append('Organ selection is required')
        if not location:
            errors.append('Location is required')
        if not phone:
            errors.append('Phone number is required')
        
        if errors:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'errors': errors})
            for error in errors:
                flash(error, 'error')
            return render_template('register.html', blood_groups=BLOOD_GROUPS, organs=ORGANS, genders=GENDERS)
        
        conn = None
        try:
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO donors (name, age, gender, email, blood_group, organ, location, phone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, int(age), gender, email, blood_group, organ, location, phone))
            conn.commit()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Registration successful! Thank you for becoming a donor.'})
            flash('Registration successful! Thank you for becoming a donor.', 'success')
            return redirect(url_for('register'))
        except sqlite3.IntegrityError:
            error_msg = 'Email already registered'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'errors': [error_msg]})
            flash(error_msg, 'error')
            return render_template('register.html', blood_groups=BLOOD_GROUPS, organs=ORGANS, genders=GENDERS)
        except sqlite3.OperationalError as e:
            error_msg = f'Database error: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'errors': [error_msg]})
            flash(error_msg, 'error')
            return render_template('register.html', blood_groups=BLOOD_GROUPS, organs=ORGANS, genders=GENDERS)
        finally:
            if conn:
                conn.close()
    
    return render_template('register.html', blood_groups=BLOOD_GROUPS, organs=ORGANS, genders=GENDERS)


@app.route('/search')
def search():
    return render_template('search.html', blood_groups=BLOOD_GROUPS, organs=ORGANS)


@app.route('/api/donors')
def api_donors():
    blood_group = request.args.get('blood_group', '').strip()
    organ = request.args.get('organ', '').strip()
    location = request.args.get('location', '').strip()
    
    conn = get_db_connection()
    query = 'SELECT * FROM donors WHERE 1=1'
    params = []
    
    if blood_group:
        query += ' AND blood_group = ?'
        params.append(blood_group)
    if organ:
        query += ' AND organ = ?'
        params.append(organ)
    if location:
        query += ' AND location LIKE ?'
        params.append(f'%{location}%')
    
    query += ' ORDER BY created_at DESC'
    
    donors = conn.execute(query, params).fetchall()
    conn.close()
    
    donors_list = []
    for donor in donors:
        donors_list.append({
            'id': donor['id'],
            'name': donor['name'],
            'age': donor['age'],
            'gender': donor['gender'],
            'email': donor['email'],
            'blood_group': donor['blood_group'],
            'organ': donor['organ'],
            'location': donor['location'],
            'phone': donor['phone'],
            'created_at': donor['created_at']
        })
    
    return jsonify({'donors': donors_list, 'count': len(donors_list)})


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        
        errors = []
        if not name:
            errors.append('Name is required')
        if not email or '@' not in email:
            errors.append('Valid email is required')
        if not subject:
            errors.append('Subject is required')
        if not message:
            errors.append('Message is required')
        
        if errors:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'errors': errors})
            for error in errors:
                flash(error, 'error')
            return render_template('contact.html')
        
        # In a real application, you would send an email here
        # For now, we just show a success message
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Message sent successfully! We will get back to you soon.'})
        flash('Message sent successfully! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    
    return render_template('contact.html')


@app.route('/api/stats')
def api_stats():
    conn = get_db_connection()
    total_donors = conn.execute('SELECT COUNT(*) as count FROM donors').fetchone()['count']
    blood_donors = conn.execute("SELECT COUNT(*) as count FROM donors WHERE organ = 'Blood Only' OR organ = 'All Organs'").fetchone()['count']
    organ_donors = conn.execute("SELECT COUNT(*) as count FROM donors WHERE organ != 'Blood Only'").fetchone()['count']
    conn.close()
    
    return jsonify({
        'total_donors': total_donors,
        'blood_donors': blood_donors,
        'organ_donors': organ_donors
    })


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
