class AppError(Exception):
    status_code = 400
    detail = "Bad request"


class EmailAlreadyExists(AppError):
    status_code = 409
    detail = "Email already registered"


class InvalidCredentials(AppError):
    status_code = 401
    detail = "Invalid email or password"


class InvalidToken(AppError):
    status_code = 401
    detail = "Invalid or expired token"


class PermissionDenied(AppError):
    status_code = 403
    detail = "Not enough permissions"


class ProductNotFound(AppError):
    status_code = 404
    detail = "Product not found"

class OrderNotFound(AppError):
    status_code = 404
    detail = "Order not found"
 
 
class ProductNotAvailable(AppError):
    status_code = 409
 
    def __init__(self, product_id):
        self.detail = f"Product {product_id} is not available"
        super().__init__(self.detail)
 
 
class InsufficientStock(AppError):
    status_code = 409
 
    def __init__(self, product_id, available: int):
        self.detail = f"Insufficient stock for product {product_id}: available {available}"
        super().__init__(self.detail)
 
 
class CannotBuyOwnProduct(AppError):
    status_code = 403
    detail = "You cannot order your own product"
 
 
class InvalidOrderState(AppError):
    status_code = 409
 
    def __init__(self, status: str):
        self.detail = f"Operation is not allowed for order in status '{status}'"
        super().__init__(self.detail)