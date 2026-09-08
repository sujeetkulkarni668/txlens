// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {TxLensPolicyVault} from "../../src/TxLensPolicyVault.sol";

/// @notice Attempts to re-enter TxLensPolicyVault.withdraw during the
///         vault's outbound call, to prove the nonReentrant guard (and the
///         checks-effects-interactions ordering) actually stops a
///         double-spend. Used only by TxLensPolicyVault.t.sol.
contract ReentrantWithdrawAttacker {
    TxLensPolicyVault public immutable vault;
    uint256 public reentrancyAttempts;
    bool public reentrancyReverted;

    constructor(TxLensPolicyVault _vault) {
        vault = _vault;
    }

    function deposit() external payable {
        vault.deposit{value: msg.value}();
    }

    function attack(uint256 amount) external {
        vault.withdraw(amount);
    }

    receive() external payable {
        reentrancyAttempts += 1;
        if (reentrancyAttempts == 1) {
            // Try to withdraw again before the first call finishes —
            // should revert due to nonReentrant.
            try vault.withdraw(msg.value) {
                reentrancyReverted = false;
            } catch {
                reentrancyReverted = true;
            }
        }
    }
}

/// @notice A target contract for executeAction calls that always reverts
///         with a distinctive message, used to prove that a failed action
///         rolls back the vault's balance/dailySpent debit.
contract AlwaysRevertingTarget {
    error TargetIntentionallyReverted();

    function poke() external payable {
        revert TargetIntentionallyReverted();
    }
}

/// @notice A benign target contract with a simple state-changing function,
///         used to prove executeAction can actually drive a contract call
///         (not just move value) when the contract is approved.
contract SimpleCounterTarget {
    uint256 public count;

    function increment() external payable {
        count += 1;
    }
}

contract ReentrantExecuteAttacker {
    TxLensPolicyVault public immutable vault;
    bool public reentrancyReverted;

    constructor(TxLensPolicyVault _vault) {
        vault = _vault;
    }

    function deposit() external payable {
        vault.deposit{value: msg.value}();
        vault.setPolicy(0, 0, false, false);
    }

    function attack() external payable {
        vault.executeAction(address(this), 0.1 ether, "");
    }

    receive() external payable {
        try vault.executeAction(address(this), 0.1 ether, "") {
            reentrancyReverted = false;
        } catch {
            reentrancyReverted = true;
        }
    }
}
