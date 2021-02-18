@export
def send(addresses: list, amount: float):
    for address in addresses:
        currency.transfer_from(amount=amount, to=address, main_account=ctx.signer)