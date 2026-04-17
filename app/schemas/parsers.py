from app.models.db_models import Transaction, User, UserBalance
from app.schemas.transaction import TransactionModel
from app.schemas.user import ResponseUserBalanceModel, ResponseUserModel


def parse_user(user: User) -> ResponseUserModel:
    result = ResponseUserModel.model_validate(user)
    if hasattr(user, "user_balance") and user.user_balance:
        result.balances = [parse_balance(b) for b in user.user_balance]
    else:
        result.balances = []
    return result


def parse_balance(balance: UserBalance) -> ResponseUserBalanceModel:
    return ResponseUserBalanceModel.model_validate(balance)


def parse_transaction(tx: Transaction) -> TransactionModel:
    return TransactionModel.model_validate(tx)
