// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/// @notice Deployment script for TxLensPolicyVault across EVM networks (Base Sepolia, Base Mainnet, Ethereum Mainnet).
/// Usage:
///   forge script script/Deploy.s.sol --rpc-url <rpc_alias_or_url> --broadcast --verify

import {Script, console2} from "forge-std/Script.sol";
import {TxLensPolicyVault} from "../src/TxLensPolicyVault.sol";

contract DeployTxLensPolicyVault is Script {
    function run() external returns (TxLensPolicyVault vault) {
        uint256 deployerKey = vm.envOr("DEPLOYER_PRIVATE_KEY", uint256(0));
        
        console2.log("Deploying TxLensPolicyVault on chain ID:", block.chainid);

        if (deployerKey != 0) {
            vm.startBroadcast(deployerKey);
        } else {
            vm.startBroadcast();
        }

        vault = new TxLensPolicyVault();

        vm.stopBroadcast();

        console2.log("--------------------------------------------------");
        console2.log("TxLensPolicyVault successfully deployed at:", address(vault));
        console2.log("--------------------------------------------------");
    }
}
