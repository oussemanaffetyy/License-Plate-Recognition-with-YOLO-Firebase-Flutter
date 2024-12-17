#Import All the Required Libraries
import json
import cv2
from ultralytics import YOLOv10
import numpy as np
import math
import re
import os
import sqlite3
from datetime import datetime
from paddleocr import PaddleOCR
import firebase_admin
from firebase_admin import credentials, firestore,messaging


os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
#Create a Video Capture Object
cap = cv2.VideoCapture("data/video2.mp4")
#Initialize the YOLOv10 Model
model = YOLOv10("weights/best.pt")
#Initialize the frame count
count = 0
#Class Names
className = ["License"]
timestamp = datetime.now()



# Charger le fichier de clé privée
cred = credentials.Certificate('json/ouswej-firebase-adminsdk-bodft-d20b5ffd9f.json')

# Initialiser Firebase
firebase_admin.initialize_app(cred)

# Initialiser Firestore
db = firestore.client()



#Initialize the Paddle OCR
ocr = PaddleOCR(use_angle_cls = True, use_gpu = True, lang = "en")

def check_license_plate(plate):
    # Charger les plaques autorisées
    authorized_plates = load_authorized_plates()

    # Normaliser la plaque détectée
    plate_normalized = plate.strip().replace("O", "0").replace("y", "").replace("Y", "")
    print(f"Checking plate: {plate} (normalized: {plate_normalized})")

    # Vérification si la plaque normalisée est dans la liste autorisée
    if plate_normalized not in authorized_plates:
        print(f"Plate {plate_normalized} is NOT authorized.")
        return False  # Plaque non autorisée
    print(f"Plate {plate_normalized} is authorized.")
    return True  # Plaque autorisée

def load_authorized_plates():
    try:
        with open('json/authorized_plates.json', 'r') as file:
            plates = json.load(file)
            # Normalisation des plaques autorisées
            plates = [plate.strip().replace("O", "0").replace("y", "").replace("Y", "") for plate in plates]
            print(f"Authorized plates: {plates}")  # Afficher les plaques autorisées après nettoyage
            return plates
    except FileNotFoundError:
        print("Authorized plates file not found!")
        return []
    

plates_logged = {}

def log_alert_to_firestore(license_plate, timestamp):
    try:
        # Créer une clé unique basée sur la plaque et la minute actuelle
        plate_key = f"{license_plate}_{timestamp.strftime('%Y-%m-%d %H:%M')}"
        
        # Vérifier si cette plaque a déjà été enregistrée pour cette minute
        if plate_key not in plates_logged:
            # Référence à la collection "alerts"
            alerts_ref = db.collection('alerts')

            # Ajouter un nouveau document à la collection avec la plaque et un timestamp
            alerts_ref.add({
                'license_plate': license_plate,
                'timestamp': firestore.SERVER_TIMESTAMP  # Timestamp serveur
            })
            print(f"Alerte ajoutée pour la plaque: {license_plate}")
            plates_logged[plate_key] = True  # Marquer cette plaque comme enregistrée pour cette minute
        else:
            print(f"Plaque {license_plate} déjà enregistrée cette minute.")
    except Exception as e:
        print(f"Erreur lors de l'ajout de l'alerte: {e}")


# Ajouter un matricule à la liste des alertes
def log_alert(license_plate, timestamp):
    # Créer une clé unique basée sur la plaque et la minute actuelle
    plate_key = f"{license_plate}_{timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    if plate_key not in plates_logged:
        alert = {
            "timestamp": datetime.now().isoformat(),
            "license_plate": license_plate
        }
        alert_file_path = "alerts.json"
        if os.path.exists(alert_file_path):
            with open(alert_file_path, 'r') as f:
                existing_alerts = json.load(f)
        else:
            existing_alerts = []

        existing_alerts.append(alert)

        with open(alert_file_path, 'w') as f:
            json.dump(existing_alerts, f, indent=2)

        plates_logged[plate_key] = True  # Marquer cette plaque comme enregistrée pour cette minute
        print(f"Plaque {license_plate} ajoutée à l'alerte.")
    else:
        print(f"Plaque {license_plate} déjà enregistrée cette minute.")




def paddle_ocr(frame, x1, y1, x2, y2):
    frame = frame[y1:y2, x1:x2]
    result = ocr.ocr(frame, det=False, rec=True, cls=False)
    text = ""
    for r in result:
        scores = r[0][1]
        if np.isnan(scores):
            scores = 0
        else:
            scores = int(scores * 100)
        if scores > 50:  # Seulement garder des résultats fiables
            text = r[0][0]

    # Afficher le texte extrait par OCR pour déboguer
    print(f"OCR detected text: {text}")

    # Nettoyage du texte détecté
    pattern = re.compile('[\W_]+')  # Enlever les caractères non-alphabétiques et les underscores
    text = pattern.sub('', text)  # Remplacer tout caractère non-alphanumérique
    text = text.replace("O", "0").replace("y", "").replace("Y", "")  # Remplacer 'O' par '0' et supprimer des lettres comme 'y'
    text = text.strip()  # Enlever les espaces superflus

    print(f"Normalized OCR text: {text}")  # Afficher le texte après nettoyage
    return str(text)




def save_json(license_plates, startTime, endTime):
    # Generate individual JSON files for each 20-second interval
    interval_data = {
        "Start Time": startTime.isoformat(),
        "End Time": endTime.isoformat(),
        "License Plate": list(license_plates)
    }
    interval_file_path = "json/output_" + datetime.now().strftime("%Y%m%d%H%M%S") + ".json"
    with open(interval_file_path, 'w') as f:
        json.dump(interval_data, f, indent=2)

    # Cumulative JSON File
    cummulative_file_path = "json/LicensePlateData.json"
    if os.path.exists(cummulative_file_path):
        with open(cummulative_file_path, 'r') as f:
            existing_data = json.load(f)
    else:
        existing_data = []

    # Add new interval data to cumulative data
    existing_data.append(interval_data)

    with open(cummulative_file_path, 'w') as f:
        json.dump(existing_data, f, indent=2)

    # Save data to SQL database
    save_to_database(license_plates, startTime, endTime)


def save_to_database(license_plates, start_time, end_time):
    conn = sqlite3.connect('licensePlatesDatabase.db')
    cursor = conn.cursor()
    for plate in license_plates:
        cursor.execute('''
            INSERT INTO LicensePlates(start_time, end_time, license_plate)
            VALUES (?, ?, ?)
        ''', (start_time.isoformat(), end_time.isoformat(), plate))
    conn.commit()
    conn.close()



# Début de la capture vidéo
startTime = datetime.now()
license_plates = set()


cv2.namedWindow("Video", cv2.WINDOW_NORMAL)
#cv2.resizeWindow("Video", 640, 480)  # Adjust window size as necessary
while True:
    ret, frame = cap.read()
    if ret:
        currentTime = datetime.now()
        count += 1
        print(f"Frame Number: {count}")
        frame_resized = cv2.resize(frame, (1080,1920))  # Réduire la taille de l'image
        results = model.predict(frame, conf=0.45)
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                classNameInt = int(box.cls[0])
                clsName = className[classNameInt]
                conf = math.ceil(box.conf[0] * 100) / 100
                
                label = paddle_ocr(frame, x1, y1, x2, y2)

                # Détecter la plaque d'immatriculation
                if label:  # Si une plaque a été détectée
                    print(f"Detected plate: {label}")  # Afficher la plaque détectée

                    # Récupérer le timestamp actuel
                    timestamp = datetime.now()

                    # Vérifier si la plaque est dans la liste autorisée
                    if not check_license_plate(label):
                        # Afficher l'alerte pour plaque non autorisée en rouge
                        alert_text = f"ALERT: Unrecognized plate: {label}"
                        log_alert_to_firestore(label, timestamp)  # Passer le timestamp
                        print(f"Unrecognized plate: {label}")  # Afficher un message d'alerte
                        cv2.putText(frame, alert_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                        log_alert(label, timestamp)  # Enregistrer l'alerte avec le timestamp
                    else:
                        # Afficher l'alerte pour plaque reconnue (autorisé) en vert
                        alert_text = f"Recognized plate: {label}"
                        print(f"Recognized plate: {label}")  # Afficher un message de reconnaissance
                        cv2.putText(frame, alert_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

                    # Ajouter la plaque détectée à la liste des plaques
                    license_plates.add(label)





                textSize = cv2.getTextSize(label, 0, fontScale=0.5, thickness=2)[0]
                c2 = x1 + textSize[0], y1 - textSize[1] - 3
                cv2.rectangle(frame, (x1, y1), c2, (255, 0, 0), -1)
                cv2.putText(frame, label, (x1, y1 - 2), 0, 0.5, [255, 255, 255], thickness=1, lineType=cv2.LINE_AA)

        # Sauvegarder les plaques toutes les 20 secondes
        if (currentTime - startTime).seconds >= 20:
            endTime = currentTime
            save_json(license_plates, startTime, endTime)
            startTime = currentTime
            license_plates.clear()

        cv2.imshow("Video", frame)
        if cv2.waitKey(1) & 0xFF == ord('1'):
            break
    else:
        break

cap.release()
cv2.destroyAllWindows()