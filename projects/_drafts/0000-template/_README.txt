

DESCRIPTION
	.txt

HASHTAGS
	.txt
	
	#has to be selected from: 
		#selected 
		#architecture
		#tech
		#art
		#music

ICON
	.png
	.jpeg
	.gif
	
	#should be squared

IMAGE[number]
	.png
	.jpeg
	.gif
	.mp4
	.mp3
	.pdf
	.txt

	MEDIA ORDER
	- Gallery media must have a numbered filename. Supported patterns are:
	  image1.jpg, image2.png, image10.gif
	  0001_plan.png, 0002_section.pdf
	- Media is displayed in ascending numeric order. Leading zeros do not
	  affect the order: image00003 is treated as number 3.
	- Files with the same number share one row and are ordered alphabetically
	  by filename, for example 0001_a.jpg beside 0001_b.jpg.
	- Unnumbered files such as plan.jpg are ignored by the gallery generator.
	- Project 0010 is a special case: its images are ordered chronologically,
	  newest first, using media-dates.json or the file creation/modification date.

TITLE
	.txt

TRAILER
	.gif
	.mp4
	.txt {if embedded}

	TRAILER ORDER
	- The trailer appears above the gallery as the project hero.
	- If multiple trailer formats exist, the priority is trailer.txt,
	  then trailer.mp4, then trailer.gif.
