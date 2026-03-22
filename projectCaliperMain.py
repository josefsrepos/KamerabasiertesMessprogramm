### Caliper Main ###
"""
Autoren:
Josef Rothermel
Jan Vagner 
Tizian Zimmer
Tim Bosch
"""


"""
offene Bugs:
- Clickfehler nach öffnen des Fensters
- Skalierungsfehler bei Fenstergröße
- Werte-Jittern 
"""

import cv2
import time
import numpy as np

### Kamera Konstanten Anfang ###

CAMERA_INDEX = 1                                                                           # 0 = interne Cam, 1 = USB-Webcam (zumindest meistens)
CAMERA_BACKEND = cv2.CAP_MSMF                                                              # Backend (Windows): MSMF = Microsoft Media Foundation (nach Tests als beste Option mit gegebener Kamera befunden)

FRAME_WIDTH = 1920                                                                         # gewünschte Breite
FRAME_HEIGHT = 1080                                                                        # gewünschte Höhe
FRAME_FPS = 30                                                                             # gewünschte FPS

FOURCC_CODEC = "MJPG"                                                                      # Motion JPEG mit 4CharakterCode

WINDOW_NAME = "Kamerabasierten Messprogramm by Bosch, Wagner, Zimmer and Rothermel"      # Titel des Fensters

### Kamera Konstanten Ende ###

### AprilTag Konstanten Anfang ###

APRILTAG_FAMILY = "25h9"                                                    # Verwendete AprilTag-Familie
MARKER_LENGTH_M = 0.039                                                     # Echte Kantenlänge des Tags in Metern (3,9 cm)
AXIS_LENGTH_M = 0.080                                                       # Länge der gezeichneten Achsen in Metern

### AprilTag Konstanten Ende ###


class CamStream:
    def __init__(
        self,
        camera_index=1,                                                             # Standard: Kamera-Index 1 (externe USB-Webcam). Index 0 -> meist interne
        backend=cv2.CAP_MSMF,                                                       # Backend (Windows): MSMF = Microsoft Media Foundation (nach Tests als beste Option mit gegebener Kamera befunden)
        width=1920,                                                                 # gewünschte Breite
        height=1080,                                                                # gewünschte Höhe
        fps=30,                                                                     # gewünschte FPS
        fourcc="MJPG",                                                              # gewünschter Codec für Stream: MJPG = Motion-JPEG (entlastet CPU bei hohen Auflösungen oft)
        window_name="Project Caliper by Bosch, Wagner, Zimmer and Rothermel",       # Fenstertitel für cv2.imshow()
    ):
        self.camera_index = camera_index                                            # Parameter in Attribute speichern für Methodenverwendung
        self.backend = backend
        self.width = width
        self.height = height
        self.fps_request = fps
        self.fourcc = fourcc
        self.window_name = window_name

        self.cap = None                                                             # Platzhalter zur besseren Lesbarkeit: Capture Objekt liefert die Frames aus cv2.VideoCapture

    def _init_camera(self):
        print("Opening camera with MSMF...please wait. This process can take up to 60 seconds!")        # Konsolenausgabe da MSMF bisschen braucht
        self.cap = cv2.VideoCapture(self.camera_index, self.backend)                                    # Erzeugen des capture Objekts

        if not self.cap.isOpened():                                                                     # Abragen der Methode isOpened (gibt true zurück wenn Kamera richtig initialisiert wurde)
            raise RuntimeError("Kamera konnte nicht geöffnet werden")                                   # Ansonsten RuntimeError setzen (Exception->Unterkategorie->Runtimeerror)

        ### Anfang CapSets (API (Schnittstelle) des CV2-Captureobjekts) ###
        # durch Zugriff durch API können werte ignoriert, anpasst oder exakt übernommen werden
        # self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)                                                      # Rausgenommer da Buffersize experimentiell gleich
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*self.fourcc))                         # MJPG setzen über FOURCC (liefert bei 1080p stabile FPS und weniger CPU-Last als unkomprimiert)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)                                              # Auflösung
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)                                            # Auflösung
        self.cap.set(cv2.CAP_PROP_FPS, self.fps_request)                                                # FPS

        ### Ende CapSets (API (Schnittstelle) des CV2-Captureobjekts) ###

        for _ in range(10):                                                                             # Warmup der Kamera mit 10 Frames (verhindern von falscher Belichtung, Autofokus etc. in den ersten Frames)
            self.cap.read()

        ret, frame = self.cap.read()                                                                    # Zusatzabfrage: ret = return of Frame (bool), frame = tatsächliches Bild (NumPy-Array)
        if not ret or frame is None:
            raise RuntimeError("Kein Frame von Kamera")

        h, w = frame.shape[:2]                                                                          # Tatsächliche Größe auslesen(:2 = ersten zwei Elemente von Frame.shape Array)
        print(f"Actual frame size: {w}x{h}")                                                            # Ausgabe

        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)                                          # Window anlegen (WINDOW_NORMAL = frei skalierbar, cv2.WINDOW_AUTOSIZE = passt sicht der Auflösung an und ist nicht skalierbar)

    @staticmethod                                               #nutzt nichts des objekts (der klasse) deshalb statisch (self wird weggelassen)
    def fps_calc(frames, fps, t0):
        frames += 1                                             #Frames inkrementieren
        dt = time.time() - t0                                   #Zeit seit t0 messen

        if dt >= 1.0:                                           #Etwa alle 1 Sekunde FPS neu berechnen
            fps = frames / dt                                   #FPS berechnen
            frames = 0                                          #Frames zurücksetzen
            t0 = time.time()                                    #t0 zurücksezuen
        return frames, fps, t0

    def run(self, fps):                                         # Ein Frame-Schritt: lesen → FPS Text → anzeigen → key zurückgeben
        if self.cap is None:
            raise RuntimeError("Camera not initialized")        # PyLance meckert sonst bei self.cap.read() -> weiß ja nichts von init_camera (zusätzliche, in dem Fall unnötige, Fehlerabsicherung)

        ret, current_frame = self.cap.read()                            # Frame holen: ret = return of Frame (bool), frame = tatsächliches Bild (NumPy-Array)

        if not ret or current_frame is None:                            # True (Errorflag) und kein Keyboardkey zurückgeben -> Führt in der while(1) schleife zu einem break
            return True, None

        cv2.putText(                                            # FPS-Text ins Bild zeichnen
            current_frame,
            f"FPS: {fps:.1f}",                                  # Anzeige mit 1 Nachkommastelle
            (20, 40),                                           # Position (x, y) in Pixeln
            cv2.FONT_HERSHEY_SIMPLEX,                           # Schriftart
            1.0,                                                # Schriftgröße (Scale)
            (32, 191, 107),                                     # Farbe (B, G, R) -> Grün aus German Palette (Flau Ui Colors)
            2,                                                  # Dicke
            cv2.LINE_AA                                         # Anti-Aliasing(Kantenglättung): glatter
        )

        return False, current_frame                            # keine errorflag zurückgeben

    def cleanup(self):
        if self.cap is not None:                                #sofern Capture Objekt existiert
            self.cap.release()                                  #kamera freigeben
        cv2.destroyAllWindows()                                 # Alle OpenCV-Fenster schließen


class AprilTagTracker:
    def __init__(self, camera_matrix, dist_coeffs, family="25h9"):

        if family == "25h9":                                                                        # Auswahl der Apriltagfamilie
            self.dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_25h9)       # Dictionary abspeichern
        else:
            raise ValueError(f"Nicht programmierte AprilTag-Familie: {family}")                     # Value Error wenn Familie nicht vorgesehen

        self.params = cv2.aruco.DetectorParameters()                                                # Detektor-Parameter Objekt (z.B. Thresholds, Eckenverfeinerung usw.)
        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.params)                       # Der eigentliche Detektor: nutzt Dictionary + Parameter

        self.camera_matrix = camera_matrix.astype(np.float64)                                       # Kameramatrix als float64 speichern
        self.dist_coeffs = dist_coeffs.astype(np.float64)                                           # Verzerrungskoeffizienten als float64 speichern

    def detect(self, current_frame, draw=True):                                                     # Übergabe des currentFrames als NumpyArray in BGR; current_frame wird in-place verändert (Mutation)
        gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)                                      # Farbraum von 3 auf 1 Graustufen des Frames

        corners, ids, rejected = self.detector.detectMarkers(gray)                                  # Marker finden, corners: Liste, pro Marker 4 Eckpunkte (im Bild), ids: Array Form (n,1)(Z,S) oder None wenn nichts gefunden
        if draw == True and ids is not None and len(ids) > 0:                                       # Nur zeichnen, wenn wirklich Tags da sind und Draw aktiviert
            cv2.aruco.drawDetectedMarkers(current_frame, corners, ids)                              # OpenCV-Hilfsfunktion: zeichnet Rahmen + IDs

        return current_frame, corners, ids, rejected                                                # Frame explizit zurückgeben + Detektionsdaten

    def estimate_pose(self, corners, marker_length_m):                                              # Pose aus Ecken + Markergröße + Kalibrierung berechnen
        rvecs, tvecs, obj_points = cv2.aruco.estimatePoseSingleMarkers(                             # cv2 Estimate Pose aufrufen
            corners,                                                                                # vier 2D Bildpunkte
            float(marker_length_m),                                                                 # Markergröße
            self.camera_matrix,                                                                     # Kameramatrix (Brennweite und Bildpunkt)
            self.dist_coeffs                                                                        # Distanz Koeeffizienten (Linsenverzerrung)
        )
        return rvecs, tvecs, obj_points                                                             # NumPyArrays für Rotationsvektoren, Translationsvektoren, 3D Eckpunkte pro Marker


    def draw_axes(self, current_frame, rvecs, tvecs, axis_length_m=0.04):
        for i in range(len(rvecs)):                                                                 # Schleife für jeden Marker / rvecs hat Shape (n,1,3) Anzahl der Marker
            rvec = rvecs[i].reshape(3, 1)                                                           # umwandeln in 3 Zeilen 1 spalte (passenden Vektor rausziehen)
            tvec = tvecs[i].reshape(3, 1)
            cv2.drawFrameAxes(                                                                      # 3D-Achsen ins Bild projizieren mit cv2 Hilfsfunktion
                current_frame,
                self.camera_matrix,
                self.dist_coeffs,
                rvec,
                tvec,
                float(axis_length_m)
            )


class PlaneMeasurementTool:
    def __init__(self, window_name, camera_matrix, dist_coeffs):
        self.window_name = window_name                                               # Name des OpenCV-Fensters (für Callback)
        self.camera_matrix = camera_matrix.astype(np.float64)                        # Kameramatrix (intrinsics), fix mit float
        self.dist_coeffs = dist_coeffs.astype(np.float64)                            # Verzerrungskoeffizienten, fix mit float

        self.rvec = None                                                             # Pose: Rotation (Marker -> Kamera)
        self.tvec = None                                                             # Pose: Translation (Marker -> Kamera)

        self.click_points_px = []                                                    # Klickpunkte in Pixeln: [(x,y), (x,y)]
        self.last_distance_m = None                                                  # zuletzt berechneter Abstand

        cv2.setMouseCallback(self.window_name, self._mouse_callback)                 # Maus-Callback ans Fenster hängen

    def set_pose(self, rvec, tvec):
        self.rvec = rvec.reshape(3, 1).astype(np.float64)                             # Pose speichern (Rotation)
        self.tvec = tvec.reshape(3, 1).astype(np.float64)                             # Pose speichern (Translation)

    def clear(self):
        self.click_points_px = []                                                     # Klickpunkte löschen
        self.last_distance_m = None                                                   # Abstand zurücksetzen

    def _mouse_callback(self, event, x, y, flags, userdata):                          # Eventweiterleitung
        if event == cv2.EVENT_LBUTTONDOWN:                                            # Linksklick -> Punkt hinzufügen
            if len(self.click_points_px) >= 2:                                        # Wenn schon 2 Punkte da sind: neu anfangen
                self.clear()
            self.click_points_px.append((int(x), int(y)))                             # Pixelpunkt speichern

        if event == cv2.EVENT_RBUTTONDOWN:                                            # Rechtsklick -> reset
            self.clear()

    def _pixel_to_ray_camera(self, pixel_point):
        # Wandelt einen Pixelpunkt in einen normierten Strahl im Kamerakoordinatensystem um (unter Berücksichtigung der camera matrix und distance coeff)

        pts = np.array([[pixel_point]], dtype=np.float64)                             # Vorbeireitung für undistortPoints
        undist_norm = cv2.undistortPoints(pts, self.camera_matrix, self.dist_coeffs)  # Ergebnis ist normiert (x,y) auf der Bildebene
        x_norm, y_norm = undist_norm[0, 0]                                            # normierte Koordinaten

        ray_dir = np.array([x_norm, y_norm, 1.0], dtype=np.float64).reshape(3, 1)     # Punkt auf Kameraebene von Umsprung aus (Vektor)
        ray_dir /= np.linalg.norm(ray_dir)                                            # normieren auf Länge 1 (optional, später wurde festegellst dass das nicht gebraucht wird)

        ray_origin = np.zeros((3, 1), dtype=np.float64)                               # Kameraursprung ist (0,0,0)
        return ray_origin, ray_dir

    def _intersect_ray_with_marker_plane(self, pixel_point):
        # Schneidet den Kamera-Strahl mit der Marker-Ebene (Marker-Z=0) und gibt den Punkt im Marker-Koordinatensystem zurück

        if self.rvec is None or self.tvec is None:
            return None                                                               # Ohne Pose keine Ebene -> Abbruch

        R, _ = cv2.Rodrigues(self.rvec)                                               # wandelt den Rotationsvektor self.rvec in eine Rotationsmatrix R

        # Marker-Ebene im Marker-KS: Z=0, Normalenvektor n_marker = [0,0,1]
        n_cam = R @ np.array([0.0, 0.0, 1.0], dtype=np.float64).reshape(3, 1)         # Normalenvektor der Ebene im Kameraraum Rechnung: Kameramatrix R @(Matrixmultiplikation) mit 0 0 1 -> normalenvektor, datatypoe float und dann reshape
        p0_cam = self.tvec                                                            # Punkt auf der Ebene im Kameraraum (Marker-Ursprung)

        ray_origin, ray_dir = self._pixel_to_ray_camera(pixel_point)                  # Strahl im Kameraraum Funktion ray_origin → Startpunkt des Strahls; ray_dir → Richtung des Strahls

        ### eigentliches Schneiden ###

        denom = float(n_cam.T @ ray_dir)                                              # Skalarprodukt n_cam.T @ ray_dir -> Nenner für Schnittpunktformel
        if abs(denom) < 1e-9:
            return None                                                               # Strahl fast parallel zur Ebene -> Abbruch

        s = float(n_cam.T @ p0_cam) / denom                                           # Skalarprodukt n_cam.T @ p0_cam -> Zähler für Schnittpunktformel 
        if s <= 0:
            return None                                                               # Schnittpunkt hinter der Kamera -> Abbruch

        intersection_cam = ray_origin + s * ray_dir                                   # Schnittpunkt im Kameraraum (n*P0/n*d)* d

        # Rücktransformieren in Marker-KS: X_marker = R^T (X_cam - t)
        intersection_marker = R.T @ (intersection_cam - self.tvec)                    # Punkt im Marker-KS durch Skalr mit Differenz 
        return intersection_marker                                                    # Form (3,1), Z sollte ~0 sein

    def update_and_draw(self, frame):
        # Zeichnet Klickpunkte, Messlinie und Abstand in den Frame, falls möglich

        # Klickpunkte im Bild markieren
        for px in self.click_points_px:                                               # für jeden Punkt in clickpointsliste
            cv2.circle(frame, px, 6, (255, 255, 255), 2, cv2.LINE_AA)                 # Punkt (weiß)

        if len(self.click_points_px) < 2:
            return frame                                                              # erst messen, wenn 2 Punkte da sind

        pointA_marker = self._intersect_ray_with_marker_plane(self.click_points_px[0])  # Punkt A auf Ebene
        pointB_marker = self._intersect_ray_with_marker_plane(self.click_points_px[1])  # Punkt B auf Ebene

        if pointA_marker is None or pointB_marker is None:                                  #error wenn keine Rückgabewerte vorhanden
            cv2.putText(frame, "Messung: Pose/Ebene nicht gueltig", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            return frame

        # Abstand im Marker-KS (Meter), 3D aber liegt in Ebene -> XY dominiert
        diff = (pointB_marker - pointA_marker).reshape(3)                             # Differenzvektor
        distance_m = float(np.linalg.norm(diff))                                      # euklidischer Abstand (Vektorbetrag)
        self.last_distance_m = distance_m

        # Linie im Bild zeichnen (einfach: Pixelpunkte verbinden)
        pA_px = self.click_points_px[0]                                               # Pixelpunkte 
        pB_px = self.click_points_px[1]
        cv2.line(frame, pA_px, pB_px, (255, 255, 255), 2, cv2.LINE_AA)                # Messlinie (weiß)

        # Text anzeigen (in cm)
        distance_cm = distance_m * 100.0
        mid_px = (int((pA_px[0] + pB_px[0]) / 2), int((pA_px[1] + pB_px[1]) / 2))     # Mitte der Linie (x,y), int() als bugfix
        cv2.putText(frame, f"{distance_cm:.1f} cm", (mid_px[0] + 10, mid_px[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

        return frame


if __name__ == "__main__":

    ### Anfang Variablen für die FPS-Messung
    t0 = time.time()                                            #Startzeitpunkt
    frames = 0                                                  #Wieviele Frames seit t0 (Zählvariable)
    fps = 0.0                                                   #Berechnete FPS
    ### Ende Variablen für die FPS-Messung ###


    ### Anfang Objekterzeugung ###
    cam_stream1 = CamStream(                                    #Erzeugung Cam Stream Obbjekt
        camera_index=CAMERA_INDEX,
        backend=CAMERA_BACKEND,
        width=FRAME_WIDTH,
        height=FRAME_HEIGHT,
        fps=FRAME_FPS,
        fourcc=FOURCC_CODEC,
        window_name=WINDOW_NAME
    )

    ### Anfang Laden Kamerakalibirierung ###
    camera_matrix = np.load("calib_data/camera_matrix.npy")      # Kamerakalibrierung laden
    dist_coeffs = np.load("calib_data/dist_coeffs.npy")
    print("Loaded camera_matrix:\n", camera_matrix)              # Print zur Fehlerbehebung
    print("Loaded dist_coeffs:\n", dist_coeffs.ravel())
    ### Ende Laden Kamerakalibirierung ###


    tracker = AprilTagTracker(camera_matrix, dist_coeffs, family=APRILTAG_FAMILY)            # Tracker Objekt erzeugen (mit Kalibriermatritzen als übergtabe)

    ### Ende Objekterzeugung ###


    ### Anfang Hauptprogramm ###
    cam_stream1._init_camera()                                                  #Initialisierung des Cam Stream
    measurer = PlaneMeasurementTool(WINDOW_NAME, camera_matrix, dist_coeffs)    #Erzeugung des Measurer Objekts
    ### Anfang Hauptprogrammschleife ###
    while True:
        frames, fps, t0 = cam_stream1.fps_calc(frames, fps, t0)                 #FPS kalkulationsmethode aufrufen und werte wieder abspeichern
        framegen_error_flag, current_frame = cam_stream1.run(fps)               #cam_Stream1.run ausführen mit FPS als Übergabewert zur Anzeige, und errorFlag und aktueller Frame als Rückgabewert
        if framegen_error_flag:                                                 #ist die errorflag geraised dann stoppe die schleife
            raise RuntimeError("Frame generation failed")                       #Error falls Framegenerierung fehlgeschlagen

        # Tracking + Zeichnen Loop direkt in frame
        if current_frame is not None:
            # 1) DETECT: Marker finden + Rahmen/IDs zeichnen
            current_frame, corners, ids, rejected = tracker.detect(
                current_frame,
                draw=True
            )

            # 2) ESTIMATE POSE: Nur wenn wirklich Marker erkannt wurden
            if ids is not None and len(ids) > 0:
                rvecs, tvecs, obj_points = tracker.estimate_pose(
                    corners,
                    marker_length_m=MARKER_LENGTH_M
                )

                # Pose für Messwerkzeug setzen (immer erster erkannter Marker)
                measurer.set_pose(rvecs[0], tvecs[0])

                # 3) DRAW AXES: Achsen pro Marker ins Bild projizieren
                tracker.draw_axes(
                    current_frame,
                    rvecs,
                    tvecs,
                    axis_length_m=AXIS_LENGTH_M
                )

                # 5) Measurer Zeichnen
                measurer.update_and_draw(current_frame)             # Messlinie + Abstand in den Frame zeichnen

            cv2.imshow(WINDOW_NAME, current_frame)                  # Frame anzeigen
        else:
            raise RuntimeError("No Frame to Show")                  # Error falls currentframe = None (pyLance meckert)

        # Fenster wurde über "X" geschlossen
        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:     # Fenster existiert nicht mehr
            break

        keyboard_press = cv2.waitKey(1) & 0xFF                      # lezten 2 Bytes maskieren (durchlassen)
        if keyboard_press == ord("c"):
            measurer.clear()                                        # Messpunkte löschen
        if keyboard_press == 27 or keyboard_press == ord("q"):      # Beenden bei ESC (27) oder q
            break
    ### Ende Hauptprogrammschleife ###

    cam_stream1.cleanup()                                          # cleanup ausführen

    ### Ende Hauptprogramm ###