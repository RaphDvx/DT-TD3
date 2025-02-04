# Basic_Implementation/app.py

from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(100), nullable=False)
    description = db.Column(String(255), nullable=True)
    price = db.Column(Float, nullable=False)
    category = db.Column(String(50), nullable=True)
    in_stock = db.Column(Boolean, default=True)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(String(50), nullable=False)  # if we track orders per user
    status = db.Column(String(50), default='pending')
    total_price = db.Column(Float, nullable=False, default=0.0)

    # relationship with OrderItem
    items = relationship('OrderItem', back_populates='order')

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(Integer, primary_key=True)
    order_id = db.Column(Integer, ForeignKey('orders.id'))
    product_id = db.Column(Integer, ForeignKey('products.id'))
    quantity = db.Column(Integer, default=1)

    order = relationship('Order', back_populates='items')
    product = relationship('Product')

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(String(50), nullable=False)
    product_id = db.Column(Integer, ForeignKey('products.id'))
    quantity = db.Column(Integer, default=1)

    product = relationship('Product')

with app.app_context():
    db.create_all()


def calculate_order_price(order):
    """ Calculate total price for an order from its items. """
    total = 0.0
    for item in order.items:
        total += item.product.price * item.quantity
    return total

def calculate_cart_total(cart_items):
    """ Calculate total price for a list of cart items. """
    total = 0.0
    for cart_item in cart_items:
        total += cart_item.product.price * cart_item.quantity
    return total

# -------------------------------------------------------
# Routes
# -------------------------------------------------------

# 1. Products
# -------------------------------------------------------
@app.route('/products', methods=['GET'])
def get_products():
    """
    GET /products
    Optional query params: category, inStock (true/false)
    """
    category = request.args.get('category')
    in_stock_str = request.args.get('inStock')

    query = Product.query
    if category:
        query = query.filter_by(category=category)
    if in_stock_str is not None:
        # expecting 'true' or 'false'
        in_stock = (in_stock_str.lower() == 'true')
        query = query.filter_by(in_stock=in_stock)

    products = query.all()
    result = []
    for product in products:
        result.append({
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'price': product.price,
            'category': product.category,
            'in_stock': product.in_stock
        })
    return jsonify(result), 200

@app.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """
    GET /products/:id
    """
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    result = {
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'category': product.category,
        'in_stock': product.in_stock
    }
    return jsonify(result), 200

@app.route('/products', methods=['POST'])
def create_product():
    """
    POST /products
    """
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    price = data.get('price', 0.0)
    category = data.get('category', '')
    in_stock = data.get('in_stock', True)

    new_product = Product(
        name=name,
        description=description,
        price=price,
        category=category,
        in_stock=in_stock
    )
    db.session.add(new_product)
    db.session.commit()

    return jsonify({
        'id': new_product.id,
        'name': new_product.name,
        'description': new_product.description,
        'price': new_product.price,
        'category': new_product.category,
        'in_stock': new_product.in_stock
    }), 201

@app.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """
    PUT /products/:id
    """
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    data = request.get_json()
    product.name = data.get('name', product.name)
    product.description = data.get('description', product.description)
    product.price = data.get('price', product.price)
    product.category = data.get('category', product.category)
    if 'in_stock' in data:
        product.in_stock = data['in_stock']

    db.session.commit()
    return jsonify({
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'category': product.category,
        'in_stock': product.in_stock
    }), 200

@app.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """
    DELETE /products/:id
    """
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    db.session.delete(product)
    db.session.commit()
    return jsonify({'message': 'Product deleted successfully'}), 200


# 2. Orders
# -------------------------------------------------------
@app.route('/orders', methods=['POST'])
def create_order():
    """
    POST /orders
    Request Body: { "user_id": "...", "products": [ { "product_id": X, "quantity": Y }, ... ] }
    """
    data = request.get_json()
    user_id = data.get('user_id')
    product_list = data.get('products', [])

    if not user_id or not product_list:
        return jsonify({'error': 'Missing user_id or products list'}), 400

    new_order = Order(user_id=user_id, status='pending', total_price=0.0)
    db.session.add(new_order)
    db.session.commit()

    # Add OrderItems
    for item in product_list:
        p_id = item.get('product_id')
        qty = item.get('quantity', 1)
        product = Product.query.get(p_id)

        if product:
            order_item = OrderItem(order_id=new_order.id, product_id=product.id, quantity=qty)
            db.session.add(order_item)

    db.session.commit()

    # Recalculate total price
    new_order.total_price = calculate_order_price(new_order)
    db.session.commit()

    # Return order details
    order_data = {
        'order_id': new_order.id,
        'user_id': new_order.user_id,
        'status': new_order.status,
        'total_price': new_order.total_price,
        'products': [
            {
                'product_id': item.product_id,
                'quantity': item.quantity,
                'product_name': item.product.name,
                'product_price': item.product.price
            } for item in new_order.items
        ]
    }
    return jsonify(order_data), 201

@app.route('/orders/<string:user_id>', methods=['GET'])
def get_orders_by_user(user_id):
    """
    GET /orders/:userId
    """
    orders = Order.query.filter_by(user_id=user_id).all()
    result = []
    for order in orders:
        result.append({
            'order_id': order.id,
            'user_id': order.user_id,
            'status': order.status,
            'total_price': order.total_price,
            'products': [
                {
                    'product_id': item.product_id,
                    'quantity': item.quantity,
                    'product_name': item.product.name,
                    'product_price': item.product.price
                } for item in order.items
            ]
        })
    return jsonify(result), 200


# 3. Cart
# -------------------------------------------------------
@app.route('/cart/<string:user_id>', methods=['POST'])
def add_to_cart(user_id):
    """
    POST /cart/:userId
    Request Body: { "product_id": X, "quantity": Y }
    """
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    if not product_id:
        return jsonify({'error': 'Missing product_id'}), 400

    # Check if product is valid
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    # Check if item already in cart
    cart_item = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()

    # Return updated cart
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    cart_data = []
    for item in cart_items:
        cart_data.append({
            'product_id': item.product_id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'price_each': item.product.price
        })

    total_cart_price = calculate_cart_total(cart_items)
    return jsonify({'cart': cart_data, 'total_price': total_cart_price}), 200

@app.route('/cart/<string:user_id>', methods=['GET'])
def get_cart(user_id):
    """
    GET /cart/:userId
    """
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    cart_data = []
    for item in cart_items:
        cart_data.append({
            'product_id': item.product_id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'price_each': item.product.price
        })

    total_cart_price = calculate_cart_total(cart_items)
    return jsonify({'cart': cart_data, 'total_price': total_cart_price}), 200

@app.route('/cart/<string:user_id>/item/<int:product_id>', methods=['DELETE'])
def remove_from_cart(user_id, product_id):
    """
    DELETE /cart/:userId/item/:productId
    """
    cart_item = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()
    if not cart_item:
        return jsonify({'error': 'Item not found in cart'}), 404

    db.session.delete(cart_item)
    db.session.commit()

    # Return updated cart
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    cart_data = []
    for item in cart_items:
        cart_data.append({
            'product_id': item.product_id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'price_each': item.product.price
        })

    total_cart_price = calculate_cart_total(cart_items)
    return jsonify({'cart': cart_data, 'total_price': total_cart_price}), 200


#Simple index.html in order for flask to work
@app.route('/')
def home():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
