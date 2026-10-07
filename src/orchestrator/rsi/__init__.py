"""rsi/ — RSI-0 offline evaluation modules (isolated experiment layer).

RSI-0 evaluates relative strategy selection only. Nothing here promotes,
trains, mutates production policy, or touches the Student. The canonical
Runtime/Broker/PEP/evidence path is reused unchanged; these modules only
serialize candidate strategies, build missions from them, run episodes, and
score persisted evidence with the hardened objective evaluator.
"""
