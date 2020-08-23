
import math

from PyQt5.QtCore import Qt, QPoint

class ConnectorLine():

	def __init__(self, *args, **kwargs):
		self.inPos = QPoint(0, 0)
		self.outPos = QPoint(25, 25)
		
		
	def isClicked(self, point, clickedThreshold):
		""" Checks if this point is within the given click threshold

			Args:
				point (QPoint): point representing the clicked location
				clickedThreshold (int): Maximum distance the point can be from the line to be considered clicking on the line
		"""
	
		#Filter out clicks that are too far from the line
		dist = distanceToLine(point.x(), point.y(), self.inPos.x(), self.inPos.y(), self.outPos.x(), self.outPos.y())
		if dist > clickedThreshold:
			return False

		offset = QPoint(self.inPos.x(), self.outPos.x())
		line = self.outPos - self.inPos
		offsetPoint = point - self.inPos

		numerator = dotProduct(line, offsetPoint)
		denominator = dotProduct(line, line)
		factor = numerator/denominator
		point = factor * line
		point += self.inPos
		
		# The dot product of 2 vectors will be negative when the angle between them is greater than 90 degrees. 
		dotproductA = (point.x() - self.inPos.x()) * (self.outPos.x() - self.inPos.x()) + (point.y() - self.inPos.y())*(self.outPos.y() - self.inPos.y())
		dotproductB = (point.x() - self.outPos.x()) * (self.outPos.x() - self.inPos.x()) + (point.y() - self.outPos.y())*(self.outPos.y() - self.inPos.y())

		if dotproductA * dotproductB > 0:
			return False

		#squaredlengthba = (self.outPos.x() - self.inPos.x())*(self.outPos.x() - self.inPos.x()) + (self.outPos.y() - self.inPos.y())*(self.outPos.y() - self.inPos.x())
		#if dotproduct > squaredlengthba:
		#	return False

		return True

	def getClickedSide(self, point):

		lineLength = math.sqrt((self.inPos.x() - self.outPos.x()) * (self.inPos.x() - self.outPos.x()) + (self.inPos.y() - self.outPos.y()) * (self.inPos.y() - self.outPos.y()))
		third = lineLength / 3

		inPosDistance = (self.inPos.x() - point.x()) * (self.inPos.x() - point.x())
		inPosDistance += (self.inPos.y() - point.y()) * (self.inPos.y() - point.y())
		inPosDistance = math.sqrt(inPosDistance)

		#If the line was clicked on the inPos side of the line. (The math here is not perfect, but good enough)
		#If the click was on the opposite side of the line (AKA, the outPos side of the line)
		if inPosDistance < third:
			return "inPos"
		elif inPosDistance > (third * 2):
			return "outPos"
		else:
			return "middle"

def distanceToLine(x0, y0, x1, y1, x2, y2):
	""" Simple helper function to calculate the distance of a point to a given line.

	Args:
		x0 - points X pos
		y0 - points Y pos
		x1 - lines starting X pos
		y1 - lines starting Y pos
		x2 - lines ending X pos
		y2 - lines ending Y pos
	"""

	numerator = abs(((y2 - y1) * x0) - ((x2 - x1) * y0) + (x2 * y1) - (y2 * x1))
	denominator = math.sqrt(((y2 - y1) * (y2 - y1)) + ((x2 - x1) * (x2 - x1)))
	return numerator/denominator


def dotProduct(v1, v2):

	dot = v1.x() * v2.x() + v1.y() + v2.y()
	return dot


"""
def smartMoveWidget(self, inPos, outPos):
		 Moves and resizes the widget so that the line fits within the min/max bounds of the widget 
		

		graceArea = 100

		#Left To Right
		if inPos.x < outPos.x:
			pass
			#Top to Bottom
			if inPos.y < outPos.y:
				pass
			else:
				pass
		else:
			pass
			

		if inPos.x() <= graceArea and inPos.y() <= graceArea:
			pass
		if inPos.x() <= graceArea and inPos.y() >= self.height() - graceArea:
			pass
		if inPos.x() >= self.width() - graceArea and inPos.y() <= graceArea:
			pass
		if inPos.x() >= self.width() - graceArea and inPos.y() <= graceArea:
			pass
	"""