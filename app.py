from flask import Flask, render_template, request, redirect, url_for,jsonify, session
import json
import mysql.connector
import os
from dotenv import load_dotenv

app = Flask(__name__)

#Random secret_key pentru fiecare user
app.secret_key = os.urandom(24) 

load_dotenv()

#functia de conectare la baza de date
def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    return conn

#Rederictionare la main.html
@app.route('/')
def index():
    return redirect(url_for('main'))

@app.route('/main', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        sex = request.form['sex']
        age = request.form['age']
        
        #Te cunectezi la baza de date
        conn = get_db_connection()
        cursor = conn.cursor()
        
        #Introdudem in baza de date varsta si sexul introuds in main
        cursor.execute("INSERT INTO users (sex, age) VALUES (%s, %s)", (sex, age))
        conn.commit()  # Commit the changes

        user_id = cursor.lastrowid  # Get the last inserted ID
        session['user_id'] = user_id  # Store user_id in session
        
        # Close the cursor and connection
        cursor.close() 
        conn.close() 
        return redirect(url_for('first_vote'))
    
    return render_template('main.html')

#First_vote, second_vote, third_vote, facem conectare la baza de date, returnam render_template la templat-ul necesar, extragem din baza de date candidatii necesari.
@app.route('/first_vote')
def first_vote():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT id, image_url, candidate_name FROM candidates LIMIT 3')
    images = cursor.fetchall()
    
    
    conn.close()

    return render_template('first_vote.html', images=images)

@app.route('/second_vote')
def second_vote():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT id, image_url, candidate_name FROM candidates ORDER BY id ASC LIMIT 3 OFFSET 3')
    images = cursor.fetchall()
    
    conn.close()

    return render_template('second_vote.html', images=images)

@app.route('/third_vote')
def third_vote():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT id, image_url, candidate_name FROM candidates order by id desc LIMIT 3')
    images = cursor.fetchall()
    
    conn.close()

    return render_template('third_vote.html', images=images)

#
@app.route('/final_vote')
def final_vote():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    #i and fvc sunt alias/shortcuts pentru candidates and final_vote_candidate tables
    #selecteaza id, image_url, candidate_name din candidates table, care o sa fie legate cu fvc prin "join candidates on final_vote_candidates.image_id = candidates.id". only first 3 rows. 
    cursor.execute('''
        SELECT i.id, i.image_url, i.candidate_name
        FROM final_vote_candidates fvc
        JOIN candidates i ON fvc.image_id = i.id
        ORDER BY fvc.id LIMIT 3
    ''')
    images = cursor.fetchall()
    
    conn.close()

    return render_template('final_vote.html', images=images)

@app.route('/results')
def results():
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Selectam datele din candidates table pentru afisarea voturilor si supreme_voturilor
    cursor.execute("""
        SELECT candidate_name, votes, supreme_vote, image_url
        FROM candidates
    """)
    candidates = cursor.fetchall()

    # Selectam datele din candidates_images pentru afisarea sub_imaginilor si cantitatii de like-uri a acestora.
    cursor.execute("""
        SELECT candidate_id, img_1, lcount1, img_2, lcount2, img_3, lcount3
        FROM candidate_images
    """)
    
    images = cursor.fetchall()

    # Cream o lista goala ca sa storam fiecare imagine cu like-urile ei.
    candidate_images = []
    for image in images:
        #Pentru fiecare row din table scoatem id, imaginea, like-urile. Toate 3 din row!
        candidate_images.append({'id': image[0], 'img': image[1], 'likes': image[2]})  # img_1 and likes
        candidate_images.append({'id': image[0], 'img': image[3], 'likes': image[4]})  # img_2 and likes
        candidate_images.append({'id': image[0], 'img': image[5], 'likes': image[6]})  # img_3 and likes

    # Sortam fiecare imagine(dictionar) dupa key:likes, in ordine descrescatoare
    candidate_images.sort(key=lambda x: x['likes'], reverse=True)

    cursor.close()
    conn.close()

    # Pass both candidate data and image data to the template
    return render_template('results.html', candidates=candidates, candidate_images=candidate_images)

#fucntia undera are loc procesul de votare
@app.route('/vote', methods=['POST'])
def vote():
    #image_id si redirect_path, ajuta sa primim informatia de la user atunci cand el apasa un button de submid de exemplu. Primim id-ul la imaginea/candidatul care l-a votat, si path-ul spre urmatoarea pagina(path-urile sunt determinate in js.)
    image_id = request.form.get('image_id')
    redirect_path = request.form.get('redirect_path')  

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
   
    #Accesam user_id ca sa facem appendin row-ul lui la ceea ce voteaza in users table din database.
    user_id = session.get('user_id')  
    
    #dupa id-ul la imagine votata facem urmatoarele operatiuni:
    if image_id:
        #selectam numele la candidat
        cursor.execute('SELECT candidate_name FROM candidates WHERE id = %s', (image_id,))
        candidate = cursor.fetchone()
        
        #!= "results" ca atunci cand dam vote la final_vote sa nu faca += 1 si la simplu vote in acelasi timp, doar la supreme_vote += 1
        if redirect_path != "results":
            #Facem insert in final_vote_candidates  numai la id(dupa dupa id accesam numele si imaginea candidatului din candidates table)
            cursor.execute('INSERT INTO final_vote_candidates (image_id) VALUES (%s)', (image_id,))
            #Dupa id votes += 1 in candidates table.
            cursor.execute('UPDATE candidates SET votes = votes + 1 WHERE id = %s', (image_id,))
            conn.commit()
        
        #Facem check daca candidate a fost gasit pentru evitarea erorilor and validation.
        if candidate:
            candidate_name = candidate['candidate_name']
            
            #Logica la codul de mai jos este: daca user-ul se razgandeste pentru cine a votat si se intoarce la pagina trecuta, acelasi candidat nu va fi in final_vote de doua ori!
            # Check if the user has already voted in the relevant round and update if needed
            if redirect_path == "second_vote":
                cursor.execute('SELECT first_vote FROM users WHERE id = %s', (user_id,))
                existing_vote = cursor.fetchone()['first_vote']
                if existing_vote:
                    # If the user already voted, update the vote
                    cursor.execute('UPDATE users SET first_vote = %s WHERE id = %s', (candidate_name, user_id))
                else:
                    # Insert the vote
                    cursor.execute('UPDATE users SET first_vote = %s WHERE id = %s', (candidate_name, user_id))
            elif redirect_path == "third_vote":
                cursor.execute('SELECT second_vote FROM users WHERE id = %s', (user_id,))
                existing_vote = cursor.fetchone()['second_vote']
                if existing_vote:
                    cursor.execute('UPDATE users SET second_vote = %s WHERE id = %s', (candidate_name, user_id))
                else:
                    cursor.execute('UPDATE users SET second_vote = %s WHERE id = %s', (candidate_name, user_id))
            elif redirect_path == "final_vote":
                cursor.execute('SELECT third_vote FROM users WHERE id = %s', (user_id,))
                existing_vote = cursor.fetchone()['third_vote']
                if existing_vote:
                    cursor.execute('UPDATE users SET third_vote = %s WHERE id = %s', (candidate_name, user_id))
                else:
                    cursor.execute('UPDATE users SET third_vote = %s WHERE id = %s', (candidate_name, user_id))
            elif redirect_path == "results":
                # Final vote logic: increment supreme vote and clear temp votes
                cursor.execute('UPDATE candidates SET supreme_vote = supreme_vote + 1 WHERE id = %s', (image_id,))
                cursor.execute('UPDATE users SET final_vote = %s WHERE id = %s', (candidate_name, user_id))
                cursor.execute('TRUNCATE TABLE final_vote_candidates')
            conn.commit()
        else:
            print(f"No candidate found for image_id: {image_id}")

    return redirect(url_for(redirect_path))
    
#Funcita colecteaza sub_imaginele si le pune intr-o lista bazat pe ID
def get_candidate_images(candidate_id):
    connection = get_db_connection()  
    cursor = connection.cursor()
    query = "SELECT img_1, img_2, img_3 FROM candidate_images WHERE candidate_id = %s"
    cursor.execute(query, (candidate_id,))
    result = cursor.fetchone()  # Fetch one row

    # Collect image paths directly from the result
    if result:
        image_paths = [result[0], result[1], result[2]]  # img_1, img_2, img_3
    else:
        image_paths = []  # No images found

    cursor.close()
    return image_paths

#Imagnile din lista de mai sus sunt convertate intr-un diactionar json
@app.route('/api/candidate_images/<int:candidate_id>', methods=['GET'])
def candidate_images(candidate_id):
        images = get_candidate_images(candidate_id)
        if not images:
            return jsonify({'error': 'No images found for this candidate'}), 404
        return jsonify({'images': images})

@app.route('/update_like', methods=['POST'])
def update_like():
    candidate_id = request.form.get('candidate_id')
    index = int(request.form.get('index'))
    is_liked = request.form.get('isLiked') == 'true'  # Convert to boolean

    conn = get_db_connection()
    cursor = conn.cursor()

    if is_liked:
        # Increment like count
        if index == 1:
            cursor.execute('UPDATE candidate_images SET lcount1 = lcount1 + 1 WHERE candidate_id = %s', (candidate_id,))
        elif index == 2:
            cursor.execute('UPDATE candidate_images SET lcount2 = lcount2 + 1 WHERE candidate_id = %s', (candidate_id,))
        elif index == 3:
            cursor.execute('UPDATE candidate_images SET lcount3 = lcount3 + 1 WHERE candidate_id = %s', (candidate_id,))
    else:
        # Decrement like count 
        if index == 1:
            cursor.execute('UPDATE candidate_images SET lcount1 = lcount1 - 1 WHERE candidate_id = %s', (candidate_id,))
        elif index == 2:
            cursor.execute('UPDATE candidate_images SET lcount2 = lcount2 - 1 WHERE candidate_id = %s', (candidate_id,))
        elif index == 3:
            cursor.execute('UPDATE candidate_images SET lcount3 = lcount3 - 1 WHERE candidate_id = %s', (candidate_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return '', 204  # No content response


if __name__ == '__main__':
    app.run(debug=True)


