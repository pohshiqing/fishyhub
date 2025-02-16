# fishyhub

This script reads product data from fishyhub db and then use gemini api to generate product description based on product name and image.

Since this user only has view access to db and cannot insert data into view, descriptions are first inserted into python array before creating the new view.

At every run, the view will be deleted (if any) and then recreated with x number of products.

