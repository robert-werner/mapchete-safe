#########
Changelog
#########

---
0.7
---
* fixed nodata masking

---
0.6
---
* group input granules by datastrip ID to make sure no redundant data is read
* make better use of NumPy to combine masks

---
0.5
---
* updated to new mapchete 0.10 API

---
0.4
---
* fixed combining bands from multiple granules
* filter cloudmasks before instaniating InputTile

---
0.3
---
* skip empty Polygons

---
0.2
---
* introduced pytest
* rewrote most parts of the API
* added example process

---
0.1
---
* initial release
