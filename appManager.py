#!/usr/bin/env python3

from flask import *  # Flask,render_template,url_for,request,redirect
from pprint import pprint
from pymongo import *
from pymongo import MongoClient
from math import dist
import random
from googlemaps import *


client = MongoClient("mongodb://127.0.0.1:27017")
db = client['dm']
request_collection = db["request"]
resource_collection = db["resource"]
user_details = db["user_details"]
resource_allocation = db["resource_allocation"]




app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

@app.route("/signup", methods=["GET", "POST"])
def sign_up():
	get_flashed_messages()
	if request.method == "POST":
		data = request.form
		data = dict(data)
		x = user_details.find_one({"name": data['username']})
		if x is not None:
			pprint(x)
			flash('User name already exists')
			return redirect(request.path)  # (url_for('sign_up'))
		mydict = {'name': data['username'], 'email': data['email'],
				  'password': data['pwd']}
		x = user_details.insert_one(mydict)
		print(data)
		flash('User name successfully registered')
		return redirect("/login")
	return render_template("sign_up.html")


@app.route("/")
@app.route("/login", methods=["GET", "POST"])
def login():
	if request.method == "POST":
		#print("Got login request")
		data = request.form
		data = dict(data)
		print(data)
		if user_details.find_one({'name':data['user_id'],'password':data['pwd']}) is None:
			flash('User name not found. Please register')
			return redirect(request.path)
		return redirect(url_for('disaster_info',usrname=data['user_id']))
		
	return render_template("login.html")



def mapsapi(address):

	latlng=GoogleMaps().address_to_latlng(address)
	return latlng


def get_priority(data):
	priority_value=0.3*data["n_affected"]+0.4*data["n_injured"]+0.3*data["mag"]
	return priority_value

def insert_into_db(data,priority_value):
	data["priority"]=priority_value
	data_local=data
	_id=request_collection.insert_one(data_local)

	return _id.inserted_id


def scheduling_algo(request_id):
	#print(request_id)
	data_x=request_collection.find({"_id":request_id})
	#print(data_x)
	for data in data_x:
		a=(data["points"][0],data["points"][1])
		resource_filter=data["resource_type"]
		unit_filter=data["n_units"]
		filter_op= {"resource_type":resource_filter , "$or":[{"n_units":{"$gt":unit_filter}},{"n_units":{"$eq":unit_filter}}]}

		candidates = resource_collection.find(filter_op)
		min_dist=float('inf')
		scheduled_resource="null"
		for x in candidates:
			b=(x["points"][0],x["points"][1])
			distance=dist(a,b)
			min_dist=min(distance,min_dist)
			scheduled_resource=x["_id"]
		if(scheduled_resource != "null"):
			#update
			res=resource_collection.find({"_id":scheduled_resource})
			for get_selected in res:
				available=get_selected["n_units"]-unit_filter
				allocated=get_selected["allocated"]+unit_filter
				resource_collection.update_one({"_id":scheduled_resource}, { "$set": {"n_units":available,"allocated":allocated}}) 

		#print(scheduled_resource)
		print("finish")
		return scheduled_resource

def getLatLong():
	lat=random.uniform(72.39627939130435, 73.26584460869566)
	long=random.uniform(19.697349876592863, 22.643130123407136)
	return lat,long

resNameToType={'food':1,'medicene':2,'shelter':3}

@app.route("/<usrname>/disaster_info", methods=["GET", "POST"])
def disaster_info(usrname):
	if request.method == "POST":
		data = request.form
		dis_info=dict(data)
		print(dis_info)
		n=len(data)-8
		req={'name':usrname,'resource_type':[],'demand':[],'allotted_location':[],'allotted_resources':[]}
		for i in range(n//2):
			tosend=dict()
			tosend={'points':[],'n_affected':int(dis_info['affected']),'n_injured':int(dis_info['injured']),'mag':float(dis_info['mag']),'resource_type':'','n_units':'','priority':''}
			tosend['resource_type']=resNameToType[data['inp'+str(i)]]
			tosend['n_units']=int(data['cnt'+str(i)])
			tosend['points']=getLatLong()
			print(tosend)
			pval=get_priority(tosend)
			id=insert_into_db(tosend,pval)
			rid=scheduling_algo(id)
			req['resource_type'].append(data['inp'+str(i)])
			req['demand'].append(data['cnt'+str(i)])
			print(rid)
			if(rid!="null"):
				f=resource_collection.find({'_id':rid})
				for x in f:
					req['allotted_location'].append(x['points'])
				req['allotted_resources'].append(data['cnt'+str(i)])
				#print(resource_collection.find({"_id":rid}))
		resource_allocation.insert_one(req)
		return redirect(url_for('dashboard',req_res=str(' '.join(req['resource_type'])),qua_ask=str(req['demand']),all_loc=str(req['allotted_location']),all_res=str(req['allotted_resources'])))
		#return redirect("/requirement")

	return render_template("disaster_info.html",usrname=usrname)

@app.route("/<req_res>/<qua_ask>/<all_loc>/<all_res>/dashboard",methods=["GET","POST"])
def dashboard(req_res,qua_ask,all_loc,all_res):
    #if request.method=="POST":
    return render_template("dashboard.html",req_res=req_res,qua_ask=qua_ask,all_loc=all_loc,all_res=all_res)



app.run(debug=True)
