import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, get_datetime
# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    current_price = {}
    transaction_history = db.execute("SELECT price, shares, stock_symbol FROM (SELECT SUM(price) AS price, SUM(shares) AS shares, stock_symbol FROM (SELECT price*shares AS price, shares, stock_symbol, user_id FROM history WHERE user_id = ?) WHERE user_id = ? GROUP BY stock_symbol) WHERE shares > 0", session["user_id"], session["user_id"])
    current_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
    total = 0
    for transaction in transaction_history:
        if transaction["stock_symbol"] in current_price:
            continue
        
        else:
            current_price[transaction["stock_symbol"]] = float(lookup(transaction["stock_symbol"])["price"])
            total += (current_price[transaction["stock_symbol"]] * transaction["shares"])
    
    total += current_cash      
    return render_template("index.html", transaction_history=transaction_history, current_price=current_price, current_cash=current_cash, total=total)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    
    if request.method == "POST":
        buysymbol = request.form.get("symbol")
        buyamount = float(request.form.get("shares"))
        buydict = lookup(buysymbol)
        rows = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        cash = float(rows[0]["cash"])
        
        if lookup(buysymbol) != None:
            if float(buydict["price"]) * buyamount > cash:
                flash(f"You don't have enough money for that! You only have {usd(cash)}")
                return render_template("buy.html")
            
            elif buyamount % 1 != 0:
                flash("Shares may only be purchased in whole numbers!")
                return render_template("buy.html")
            
            else:
                db.execute("UPDATE users SET cash = ? WHERE id = ?", cash - (float(buydict["price"]) * buyamount), session["user_id"])
                db.execute("INSERT INTO history (user_id, transaction_date, price, shares, stock_symbol) VALUES (?, ?, ?, ?, ?)", session["user_id"], get_datetime(), float(buydict["price"]), int(buyamount), buydict["symbol"])
                flash("Success! Stock bought!")
                return redirect("/")
        
        else:
            flash("Invalid stock symbol!", "error")
            return render_template("buy.html")
              
    else:
        if "quoted" in session:
            quote= session["quoted"]
            session.pop("quoted")
            
        else:
            quote= None
        return render_template("buy.html", quote=quote)
        

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    
    transactions = db.execute("SELECT * FROM history WHERE user_id = ?", session["user_id"])
    
    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    
    postsymbol= request.form.get("postsymbol")
    """Get stock quote."""
    if request.method == "POST":
        
        if lookup(postsymbol) == None:
            flash("Invalid stock symbol!", "error")
            return render_template("quote.html")
        
        else: 
            stockdict= lookup(postsymbol)
            symbol= stockdict["symbol"]
            name= stockdict["name"]
            price= usd(stockdict["price"])
            session["quoted"] = symbol
            return render_template("quoted.html", name=name, symbol=symbol, price=price, postsymbol=postsymbol)
    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        
        if not request.form.get("username"):
            flash("Must provide a username!", "error")
            return render_template("register.html")
        
        elif not request.form.get("password"):
            flash("Must provide a password!", "error")
            return render_template("register.html")
        
        elif len(request.form.get("password")) < 8 or len(request.form.get("password")) > 16:
            flash("Password must be 8-16 characters long!", "error")
            return render_template("register.html")
                 
        elif not (request.form.get("password").isalnum() and any(i.isnumeric() for i in request.form.get("password")) and any(j.isalpha() for j in request.form.get("password"))):
            flash("Password must be alphanumeric containing at least 1 number and 1 letter", "error")
            return render_template("register.html")
        
        elif request.form.get("password") != request.form.get("confirmation"):
            flash("Passwords do not match!", "error")
            return render_template("register.html")
        
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        
        if len(rows) != 0:
            flash("Username already exists!", "error")
            return render_template("register.html")
        
        hash_pass= generate_password_hash(request.form.get("password"))
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get("username"), hash_pass)
        
        flash("Success! Please log in with your new username and password!")
        return render_template("login.html")
    
    else:
        return render_template("register.html")
    


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        if not request.form.get("stock"):
            flash("Please provide a stock symbol!")
            return render_template("sell.html")
        
        elif lookup(request.form.get("stock")) == None:
            flash("invalid stock signal!")
            return render_template("sell.html")
        
        elif not request.form.get("shares"):
            flash("Please provide the number of shares you would like to sell!")
            return render_template("sell.html")
                
        else:
            stock = request.form.get("stock").upper()
            shares = int(request.form.get("shares"))
            owned_shares = db.execute("SELECT SUM(shares) AS shares_owned, stock_symbol FROM history WHERE user_id = ? AND stock_symbol = ?", session["user_id"], stock)

        if owned_shares[0]["shares_owned"] == None:
            flash("You do not own any of this stock!")
            return render_template("sell.html")
        
        if shares > owned_shares[0]["shares_owned"]:
            flash(f"You don't own enough shares of {stock} to complete this sale!")
            return render_template("sell.html")

        if shares % 1 != 0:
            flash("Please enter a whole number of shares to sell!")
            return render_template("sell.html")
        
        sell_shares = -1 * int(shares)
        sell_price = lookup(stock)["price"]
        db.execute("INSERT INTO history (user_id, transaction_date, price, shares, stock_symbol) VALUES (?, ?, ?, ?, ?)", session["user_id"], get_datetime(), sell_price, sell_shares, stock)
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash + ((-1 * sell_shares)*(sell_price)), session["user_id"])
        flash("Sale Successful!")
        
        return redirect("/")
        
    else:
        return render_template("sell.html")


