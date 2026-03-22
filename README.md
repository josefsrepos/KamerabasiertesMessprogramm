# Caliper
2D/3D Measurement with ArUrco Markers

Developer Notes:

 -  Umbedingt MSMF (Microsoft Media Foundation) als Capture Backend verwenden: ~30 FPS bei 1080p   mit MJPG. Als Pipeline: Device → MediaType → Decoder → Konvertierung → Frames (liefert Stream MJPG 1920×1080 @30)

 -  Dokumentation siehe Repo