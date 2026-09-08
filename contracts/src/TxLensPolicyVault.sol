// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/// @title TxLensPolicyVault
/// @notice Demonstrates real, enforceable on-chain policy logic (product spec
///         section 19). Each account manages its own sub-balance and its own
///         policy inside this single shared contract — there is no privileged
///         global owner/admin role, so no single key can move another user's
///         funds or override their policy.
///
/// @dev IMPORTANT — read before relying on this in any deployment:
///      1. This contract can only enforce policy on funds and calls that are
///         routed THROUGH it. It cannot block, inspect, or influence any
///         transaction a user signs directly from their own EOA outside this
///         contract — TxLens never claims otherwise (see SECURITY.md).
///      2. `executeAction` forwards `data` verbatim to `recipient` via a raw
///         `.call`. That is the entire point (executing an approved action
///         on the user's behalf) but it means the policy checks below —
///         amount limits, approved recipients, approved contracts — are the
///         ONLY protection against an arbitrary call. Users who want strong
///         protection against unexpected calldata should enable
///         `useApprovedContracts` and only approve contracts they trust.
///      3. This contract deliberately never uses `delegatecall` — a target
///         contract can never take over this vault's storage.
///      4. NOT COMPILED OR TESTED in the environment that generated this
///         file: no `solc`/`forge` were available (no network, no Docker).
///         Treat this as an unverified draft until `forge build` and
///         `forge test` have actually been run against it.
contract TxLensPolicyVault {
    // ── Types ────────────────────────────────────────────────────────

    struct Policy {
        bool isSet; // must be true before executeAction will accept anything
        uint256 maxTransactionAmount; // 0 = no per-transaction cap
        uint256 dailySpendLimit; // 0 = no daily cap
        bool useApprovedRecipients; // if true, recipient must be pre-approved
        bool useApprovedContracts; // if true, calls with data must target a pre-approved contract
    }

    // ── Storage ──────────────────────────────────────────────────────

    mapping(address => uint256) public balances;
    mapping(address => Policy) public policies;
    mapping(address => mapping(address => bool)) public approvedRecipients;
    mapping(address => mapping(address => bool)) public approvedContracts;

    mapping(address => uint256) public dailySpent;
    mapping(address => uint256) public dailyWindowStart;

    uint256 public constant DAILY_WINDOW = 1 days;

    // Minimal reentrancy guard — avoids depending on an external library so
    // this file has no import-path/remapping requirements to get wrong.
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;
    uint256 private _reentrancyStatus = _NOT_ENTERED;

    modifier nonReentrant() {
        require(_reentrancyStatus != _ENTERED, "TxLensPolicyVault: reentrant call");
        _reentrancyStatus = _ENTERED;
        _;
        _reentrancyStatus = _NOT_ENTERED;
    }

    // ── Events ───────────────────────────────────────────────────────

    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event PolicySet(
        address indexed user,
        uint256 maxTransactionAmount,
        uint256 dailySpendLimit,
        bool useApprovedRecipients,
        bool useApprovedContracts
    );
    event ApprovedRecipientUpdated(address indexed user, address indexed recipient, bool approved);
    event ApprovedContractUpdated(address indexed user, address indexed target, bool approved);
    event ActionExecuted(address indexed user, address indexed recipient, uint256 amount, bytes data);

    // ── Deposits / withdrawals ───────────────────────────────────────

    /// @notice Deposit native currency into the caller's own vault balance.
    function deposit() external payable {
        balances[msg.sender] += msg.value;
        emit Deposited(msg.sender, msg.value);
    }

    receive() external payable {
        balances[msg.sender] += msg.value;
        emit Deposited(msg.sender, msg.value);
    }

    /// @notice Withdraw the caller's own funds back to themselves. Not
    ///         subject to policy checks — it is the user's own money going
    ///         to their own address, not a delegated action.
    function withdraw(uint256 amount) external nonReentrant {
        require(amount > 0, "TxLensPolicyVault: amount must be > 0");
        require(balances[msg.sender] >= amount, "TxLensPolicyVault: insufficient balance");

        // Effects before interaction (checks-effects-interactions).
        balances[msg.sender] -= amount;

        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "TxLensPolicyVault: withdraw transfer failed");

        emit Withdrawn(msg.sender, amount);
    }

    // ── Policy configuration ─────────────────────────────────────────

    /// @notice Configure the caller's policy. Must be called at least once
    ///         (isSet becomes true) before executeAction will accept anything
    ///         — there is no implicit "unlimited by default" state.
    /// @param maxTransactionAmount 0 means no per-transaction cap.
    /// @param dailySpendLimit 0 means no daily cap.
    function setPolicy(
        uint256 maxTransactionAmount,
        uint256 dailySpendLimit,
        bool useApprovedRecipients,
        bool useApprovedContracts
    ) external {
        policies[msg.sender] = Policy({
            isSet: true,
            maxTransactionAmount: maxTransactionAmount,
            dailySpendLimit: dailySpendLimit,
            useApprovedRecipients: useApprovedRecipients,
            useApprovedContracts: useApprovedContracts
        });

        emit PolicySet(
            msg.sender, maxTransactionAmount, dailySpendLimit, useApprovedRecipients, useApprovedContracts
        );
    }

    function setApprovedRecipient(address recipient, bool approved) external {
        require(recipient != address(0), "TxLensPolicyVault: zero address");
        approvedRecipients[msg.sender][recipient] = approved;
        emit ApprovedRecipientUpdated(msg.sender, recipient, approved);
    }

    function setApprovedContract(address target, bool approved) external {
        require(target != address(0), "TxLensPolicyVault: zero address");
        approvedContracts[msg.sender][target] = approved;
        emit ApprovedContractUpdated(msg.sender, target, approved);
    }

    // ── Policy-gated execution ───────────────────────────────────────

    /// @notice Execute a native-value transfer and/or contract call from the
    ///         caller's own vault balance, enforcing the caller's own policy.
    ///         Reverts (with a descriptive reason) rather than silently
    ///         doing nothing if the action violates policy — the "reject"
    ///         behavior in product spec section 19 is this revert.
    function executeAction(address recipient, uint256 amount, bytes calldata data)
        external
        nonReentrant
    {
        require(recipient != address(0), "TxLensPolicyVault: zero address recipient");

        Policy memory policy = policies[msg.sender];
        require(policy.isSet, "TxLensPolicyVault: no policy configured");
        require(balances[msg.sender] >= amount, "TxLensPolicyVault: insufficient vault balance");

        if (policy.maxTransactionAmount != 0) {
            require(
                amount <= policy.maxTransactionAmount,
                "TxLensPolicyVault: exceeds max transaction amount"
            );
        }

        if (policy.useApprovedRecipients) {
            require(
                approvedRecipients[msg.sender][recipient],
                "TxLensPolicyVault: recipient not approved"
            );
        }

        if (policy.useApprovedContracts && data.length > 0) {
            require(
                approvedContracts[msg.sender][recipient],
                "TxLensPolicyVault: contract not approved"
            );
        }

        // Daily window reset (lazy — only touches storage when a new
        // window has actually started).
        if (block.timestamp >= dailyWindowStart[msg.sender] + DAILY_WINDOW) {
            dailyWindowStart[msg.sender] = block.timestamp;
            dailySpent[msg.sender] = 0;
        }

        if (policy.dailySpendLimit != 0) {
            require(
                dailySpent[msg.sender] + amount <= policy.dailySpendLimit,
                "TxLensPolicyVault: exceeds daily spend limit"
            );
        }

        // Effects before interaction.
        balances[msg.sender] -= amount;
        dailySpent[msg.sender] += amount;

        // Intentionally a raw `.call`, never `delegatecall` — see contract
        // NatSpec. Deliberately does NOT swallow failure: if the target
        // reverts, this whole action reverts and the effects above are
        // rolled back too, so the user's balance/dailySpent are never
        // debited for an action that didn't actually happen.
        (bool success, bytes memory returndata) = recipient.call{value: amount}(data);
        if (!success) {
            // Bubble up the target's revert reason if it gave one, rather
            // than masking it behind a generic message.
            if (returndata.length > 0) {
                assembly {
                    let returndata_size := mload(returndata)
                    revert(add(32, returndata), returndata_size)
                }
            }
            revert("TxLensPolicyVault: action execution failed");
        }

        emit ActionExecuted(msg.sender, recipient, amount, data);
    }

    // ── Views ────────────────────────────────────────────────────────

    /// @notice Daily spend accounting for a window reset that hasn't been
    ///         written to storage yet (a pure read never mutates state).
    function getEffectiveDailySpent(address user) external view returns (uint256) {
        if (block.timestamp >= dailyWindowStart[user] + DAILY_WINDOW) {
            return 0;
        }
        return dailySpent[user];
    }
}
