from weakref import WeakKeyDictionary

class descriptor():	
	def __init__(self, defaultValue=None):
		self.data = {} #WeakKeyDictionary()
		self.defaultValue = defaultValue

	def __get__(self, instance, instance_type):
		if instance:
			return self.data.get(instance, self.defaultValue)
		else:
			return self.defaultValue

	def __set__(self, instance, value):
		self.data[instance] = value
		

class meta(type):
	__slots__ = []

class task(metaclass=meta):
	desc = descriptor(defaultValue=None)

	def __init__(self):
		pass


obj1 = task()
obj2 = task()



print("Before")
print(obj1.desc)
print(obj2.desc)

obj1.desc = "A DESCRIPTOR"

print("after")
print(obj1.desc)
print(obj2.desc)

print (obj1.__dict__)


print (obj1.__dict__)

print (obj1.desc)

testObj = obj1.__dict__['desc']
print(testObj)

