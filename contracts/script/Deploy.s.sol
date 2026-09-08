// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

// NOT RUN in the environment that generated this file — no forge available.
// Validate with: forge script script/Deploy.s.sol --rpc-url $EVM_RPC_URL --broadcast

import {Script, console} from "forge-std/Script.sol";
import {TxLensPolicyVault} from "../src/TxLensPolicyVault.sol";

contract DeployTxLensPolicyVault is Script {
    function run() external returns (TxLensPolicyVault vault) {
        uint256 deployerKey = vm.envUint("DEPLOYER_PRIVATE_KEY");

        vm.startBroadcast(deployerKey);
        vault = new TxLensPolicyVault();
        vm.stopBroadcast();

        console.log("TxLensPolicyVault deployed at:", address(vault));
    }
}
