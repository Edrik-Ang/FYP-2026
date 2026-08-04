from django.test import TestCase

# Create your tests here.

## test for authentication
# 

## Test for Context
# list contexts --> Expected 200
# create context --> Expected 201
# update context --> Expected 200
# delete context --> Expected 204
# reject duplicate context name --> 400
# cannot delete context with identities --> 400
# cannot edt another user's context --> 404
# cannot delete another user's context --> 404

## Test for Identity
# list identities --> Expected 200
# create identity --> Expected 201
# create with someone else's context --> 400
# update identity --> Expected 200
#move identity to nother owned context --> Expected 200
# Move identity to another user's context --> 400
# delete identity --> Expected 204
# retireve another user's identity --> 404

## Test for Relationship
# list relationships --> Expected 200
# create relationship --> Expected 201
# cannot related to yourself --> 400
# cannot use another user's context --> 400
# cannot create duplicate relationship --> 400
# must have at least 1 context --> 400
# update contexts --> Expected 200
# Delete relationship --> Expected 204
# cannot view another user's relationship --> 404


## Test for disclosure
# List own rules --> Expected 200
# Create rules --> 201
# update Visibility --> 200
# Delete rules --> 204
# Cannot use another user's identity or context --> 400
# cannot use public context --> 400
# Cannot retrieve another user's rule --> 404
