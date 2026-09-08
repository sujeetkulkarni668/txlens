// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

// NOT COMPILED OR RUN in the environment that generated this file — no
// forge/solc available (no network, no Docker). Validate for real with:
//   forge install foundry-rs/forge-std
//   forge build
//   forge test -vvv

import {Test} from "forge-std/Test.sol";
import {TxLensPolicyVault} from "../src/TxLensPolicyVault.sol";
import {
    ReentrantWithdrawAttacker,
    AlwaysRevertingTarget,
    SimpleCounterTarget
} from "./mocks/TestHelpers.sol";

contract TxLensPolicyVaultTest is Test {
    TxLensPolicyVault internal vault;

    address internal alice = address(0xA11CE);
    address internal bob = address(0xB0B);
    address internal recipient = address(0xCAFE);

    function setUp() public {
        vault = new TxLensPolicyVault();
        vm.deal(alice, 100 ether);
        vm.deal(bob, 100 ether);
    }

    // ── Deposits ─────────────────────────────────────────────────────

    function test_deposit_increases_balance() public {
        vm.prank(alice);
        vault.deposit{value: 1 ether}();
        assertEq(vault.balances(alice), 1 ether);
    }

    function test_receive_also_credits_sender() public {
        vm.prank(alice);
        (bool ok, ) = address(vault).call{value: 1 ether}("");
        assertTrue(ok);
        assertEq(vault.balances(alice), 1 ether);
    }

    function test_withdraw_returns_funds_and_decrements_balance() public {
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        uint256 balanceBefore = alice.balance;
        vault.withdraw(0.4 ether);
        vm.stopPrank();

        assertEq(vault.balances(alice), 0.6 ether);
        assertEq(alice.balance, balanceBefore + 0.4 ether);
    }

    function test_withdraw_more_than_balance_reverts() public {
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vm.expectRevert("TxLensPolicyVault: insufficient balance");
        vault.withdraw(2 ether);
        vm.stopPrank();
    }

    // ── Policy gate ──────────────────────────────────────────────────

    function test_execute_action_without_policy_reverts() public {
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vm.expectRevert("TxLensPolicyVault: no policy configured");
        vault.executeAction(recipient, 0.1 ether, "");
        vm.stopPrank();
    }

    function test_execute_action_succeeds_once_policy_is_set() public {
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vault.setPolicy(0, 0, false, false);
        vault.executeAction(recipient, 0.1 ether, "");
        vm.stopPrank();

        assertEq(vault.balances(alice), 0.9 ether);
        assertEq(recipient.balance, 0.1 ether);
    }

    // ── Maximum transaction amount ───────────────────────────────────

    function test_blocks_transaction_over_max_amount() public {
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vault.setPolicy(0.5 ether, 0, false, false);
        vm.expectRevert("TxLensPolicyVault: exceeds max transaction amount");
        vault.executeAction(recipient, 0.6 ether, "");
        vm.stopPrank();
    }

    function test_allows_transaction_at_exactly_max_amount() public {
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vault.setPolicy(0.5 ether, 0, false, false);
        vault.executeAction(recipient, 0.5 ether, "");
        vm.stopPrank();
        assertEq(vault.balances(alice), 0.5 ether);
    }

    function test_zero_max_amount_means_unlimited() public {
        vm.startPrank(alice);
        vault.deposit{value: 10 ether}();
        vault.setPolicy(0, 0, false, false);
        vault.executeAction(recipient, 9 ether, "");
        vm.stopPrank();
        assertEq(vault.balances(alice), 1 ether);
    }

    // ── Daily spend limit ────────────────────────────────────────────

    function test_blocks_when_daily_limit_exceeded() public {
        vm.startPrank(alice);
        vault.deposit{value: 5 ether}();
        vault.setPolicy(0, 1 ether, false, false);
        vault.executeAction(recipient, 0.6 ether, "");
        vm.expectRevert("TxLensPolicyVault: exceeds daily spend limit");
        vault.executeAction(recipient, 0.6 ether, ""); // 0.6 + 0.6 > 1.0
        vm.stopPrank();
    }

    function test_daily_limit_resets_after_window() public {
        vm.startPrank(alice);
        vault.deposit{value: 5 ether}();
        vault.setPolicy(0, 1 ether, false, false);
        vault.executeAction(recipient, 0.9 ether, "");

        vm.warp(block.timestamp + 1 days + 1);
        // Should succeed again now that the window has rolled over.
        vault.executeAction(recipient, 0.9 ether, "");
        vm.stopPrank();

        assertEq(vault.balances(alice), 5 ether - 1.8 ether);
    }

    function test_effective_daily_spent_view_reflects_unrealized_reset() public {
        vm.startPrank(alice);
        vault.deposit{value: 5 ether}();
        vault.setPolicy(0, 1 ether, false, false);
        vault.executeAction(recipient, 0.5 ether, "");
        assertEq(vault.getEffectiveDailySpent(alice), 0.5 ether);

        vm.warp(block.timestamp + 1 days + 1);
        // Storage hasn't been touched yet, but the view should still
        // report 0 since the window has conceptually rolled over.
        assertEq(vault.getEffectiveDailySpent(alice), 0);
        vm.stopPrank();
    }

    // ── Approved recipients ──────────────────────────────────────────

    function test_blocks_unapproved_recipient_when_flag_enabled() public {
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vault.setPolicy(0, 0, true, false);
        vm.expectRevert("TxLensPolicyVault: recipient not approved");
        vault.executeAction(recipient, 0.1 ether, "");
        vm.stopPrank();
    }

    function test_allows_approved_recipient() public {
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vault.setApprovedRecipient(recipient, true);
        vault.setPolicy(0, 0, true, false);
        vault.executeAction(recipient, 0.1 ether, "");
        vm.stopPrank();
        assertEq(recipient.balance, 0.1 ether);
    }

    // ── Approved contracts ───────────────────────────────────────────

    function test_blocks_unapproved_contract_call() public {
        SimpleCounterTarget target = new SimpleCounterTarget();
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vault.setPolicy(0, 0, false, true);
        vm.expectRevert("TxLensPolicyVault: contract not approved");
        vault.executeAction(address(target), 0, abi.encodeCall(SimpleCounterTarget.increment, ()));
        vm.stopPrank();
    }

    function test_allows_approved_contract_call_and_it_actually_executes() public {
        SimpleCounterTarget target = new SimpleCounterTarget();
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vault.setApprovedContract(address(target), true);
        vault.setPolicy(0, 0, false, true);
        vault.executeAction(address(target), 0, abi.encodeCall(SimpleCounterTarget.increment, ()));
        vm.stopPrank();
        assertEq(target.count(), 1);
    }

    function test_plain_value_transfer_not_subject_to_contract_approval() public {
        // useApprovedContracts only gates calls that carry calldata — a
        // plain value transfer (empty data) to an un-approved address
        // should still be governed by useApprovedRecipients, not this flag.
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vault.setPolicy(0, 0, false, true);
        vault.executeAction(recipient, 0.1 ether, "");
        vm.stopPrank();
        assertEq(recipient.balance, 0.1 ether);
    }

    // ── Malformed parameters ─────────────────────────────────────────

    function test_zero_address_recipient_reverts() public {
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vault.setPolicy(0, 0, false, false);
        vm.expectRevert("TxLensPolicyVault: zero address recipient");
        vault.executeAction(address(0), 0.1 ether, "");
        vm.stopPrank();
    }

    function test_zero_address_approved_recipient_reverts() public {
        vm.prank(alice);
        vm.expectRevert("TxLensPolicyVault: zero address");
        vault.setApprovedRecipient(address(0), true);
    }

    // ── Insufficient balance ─────────────────────────────────────────

    function test_execute_action_over_balance_reverts() public {
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vault.setPolicy(0, 0, false, false);
        vm.expectRevert("TxLensPolicyVault: insufficient vault balance");
        vault.executeAction(recipient, 2 ether, "");
        vm.stopPrank();
    }

    // ── Unauthorized execution / cross-user isolation ────────────────

    function test_alice_cannot_spend_bobs_balance() public {
        vm.prank(bob);
        vault.deposit{value: 5 ether}();

        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vault.setPolicy(0, 0, false, false);
        vault.executeAction(recipient, 1 ether, "");
        vm.stopPrank();

        // Alice's action only ever touched her own balance.
        assertEq(vault.balances(alice), 0);
        assertEq(vault.balances(bob), 5 ether);
    }

    function test_alices_policy_does_not_affect_bob() public {
        vm.prank(alice);
        vault.setPolicy(0.1 ether, 0, false, false);

        vm.startPrank(bob);
        vault.deposit{value: 1 ether}();
        vault.setPolicy(0, 0, false, false); // Bob sets his own, unrestricted
        vault.executeAction(recipient, 0.9 ether, ""); // would violate Alice's cap, not Bob's
        vm.stopPrank();

        assertEq(vault.balances(bob), 0.1 ether);
    }

    // ── Reentrancy ───────────────────────────────────────────────────

    function test_reentrant_withdraw_is_blocked() public {
        ReentrantWithdrawAttacker attacker = new ReentrantWithdrawAttacker(vault);
        vm.deal(address(attacker), 2 ether);

        vm.prank(address(attacker));
        // Deposit MORE than the reentrant attempt will try to withdraw —
        // if the nonReentrant guard weren't there, the leftover 1 ether
        // balance would be enough for the reentrant withdraw(1 ether) to
        // succeed on its own merits (checks-effects-interactions alone
        // would NOT have caught this one, since there's genuinely enough
        // balance left). This isolates what the guard specifically buys.
        attacker.deposit{value: 2 ether}();

        vm.prank(address(attacker));
        attacker.attack(1 ether);

        assertEq(attacker.reentrancyAttempts(), 1);
        assertTrue(attacker.reentrancyReverted());
        // Only the first, legitimate withdrawal went through.
        assertEq(vault.balances(address(attacker)), 1 ether);
        assertEq(address(attacker).balance, 1 ether);
    }

    // ── Unsafe external calls: failed action rolls back state ────────

    function test_failed_action_call_reverts_and_preserves_balance() public {
        AlwaysRevertingTarget target = new AlwaysRevertingTarget();
        vm.startPrank(alice);
        vault.deposit{value: 1 ether}();
        vault.setApprovedContract(address(target), true);
        vault.setPolicy(0, 0, false, true);

        vm.expectRevert(AlwaysRevertingTarget.TargetIntentionallyReverted.selector);
        vault.executeAction(address(target), 0, abi.encodeCall(AlwaysRevertingTarget.poke, ()));
        vm.stopPrank();

        // Balance must be exactly what it was before the failed attempt —
        // effects-before-interaction alone isn't enough without the
        // revert propagating and rolling the whole transaction back.
        assertEq(vault.balances(alice), 1 ether);
    }

    // ── "Replay" — see note ──────────────────────────────────────────

    /// @dev This contract has no signature/meta-transaction surface: every
    /// action is authenticated directly by msg.sender, not by a signed
    /// message someone else relays on the user's behalf. There is
    /// therefore no classic "replay a captured signature" vector for a
    /// nonce to defend against. What IS worth asserting is the corollary:
    /// two separate, freshly-authorized calls with identical arguments
    /// are each independently valid — repeating a call is not itself
    /// forbidden, since it is not a replay, it is a new authorized action.
    function test_identical_repeated_calls_are_independently_valid_not_a_replay() public {
        vm.startPrank(alice);
        vault.deposit{value: 2 ether}();
        vault.setPolicy(0, 0, false, false);
        vault.executeAction(recipient, 0.5 ether, "");
        vault.executeAction(recipient, 0.5 ether, "");
        vm.stopPrank();

        assertEq(vault.balances(alice), 1 ether);
        assertEq(recipient.balance, 1 ether);
    }
}
