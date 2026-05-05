// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

interface IERC20 {
    function transferFrom(address from, address to, uint256 value) external returns (bool);
}

contract PaymentProcessor {
    address public owner;
    mapping(address => bool) public operators;
    mapping(bytes32 => bool) public processedPayments;
    mapping(address => bool) public allowedTokens;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event OperatorUpdated(address indexed operator, bool allowed);
    event TokenUpdated(address indexed token, bool allowed);
    event PaymentProcessed(
        bytes32 indexed paymentId,
        address indexed token,
        address indexed from,
        address to,
        uint256 amount,
        address operator
    );

    error NotOwner();
    error NotOperator();
    error TokenNotAllowed();
    error InvalidAddress();
    error InvalidAmount();
    error PaymentAlreadyProcessed();
    error TransferFailed();

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlyOperator() {
        if (!operators[msg.sender]) revert NotOperator();
        _;
    }

    constructor(address initialOwner, address initialOperator, address initialToken) {
        if (initialOwner == address(0)) revert InvalidAddress();
        if (initialOperator == address(0)) revert InvalidAddress();
        if (initialToken == address(0)) revert InvalidAddress();

        owner = initialOwner;
        operators[initialOperator] = true;
        allowedTokens[initialToken] = true;

        emit OwnershipTransferred(address(0), initialOwner);
        emit OperatorUpdated(initialOperator, true);
        emit TokenUpdated(initialToken, true);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert InvalidAddress();
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    function setOperator(address operator, bool allowed) external onlyOwner {
        if (operator == address(0)) revert InvalidAddress();
        operators[operator] = allowed;
        emit OperatorUpdated(operator, allowed);
    }

    function setToken(address token, bool allowed) external onlyOwner {
        if (token == address(0)) revert InvalidAddress();
        allowedTokens[token] = allowed;
        emit TokenUpdated(token, allowed);
    }

    function pay(
        bytes32 paymentId,
        address token,
        address from,
        address to,
        uint256 amount
    ) external onlyOperator {
        if (!allowedTokens[token]) revert TokenNotAllowed();
        if (from == address(0) || to == address(0)) revert InvalidAddress();
        if (amount == 0) revert InvalidAmount();
        if (processedPayments[paymentId]) revert PaymentAlreadyProcessed();

        processedPayments[paymentId] = true;

        bool success = IERC20(token).transferFrom(from, to, amount);
        if (!success) revert TransferFailed();

        emit PaymentProcessed(paymentId, token, from, to, amount, msg.sender);
    }
}
