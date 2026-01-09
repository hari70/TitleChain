// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title TitleRegistry
 * @notice Anchors title credentials and tracks ownership on-chain
 * @dev Minimal on-chain data for privacy; full data in VCs
 * 
 * This contract provides:
 * - Credential hash anchoring (proof of existence + timestamp)
 * - Property registration
 * - Ownership transfer recording
 * 
 * TODO: Deploy to Polygon Mumbai testnet for testing
 * TODO: Add access control for authorized issuers
 * TODO: Integrate with backend credential_issuer.py
 */
contract TitleRegistry {
    
    struct PropertyAnchor {
        bytes32 currentTitleVCHash;      // Hash of current PropertyTitleVC
        bytes32 currentOwnerDIDHash;     // Hash of owner's DID
        uint256 lastUpdated;             // Timestamp
        uint256 transferCount;           // Number of ownership changes
        bool isActive;                   // Property exists in system
    }
    
    // Property DID hash → PropertyAnchor
    mapping(bytes32 => PropertyAnchor) public properties;
    
    // Credential hash → timestamp (proof of existence)
    mapping(bytes32 => uint256) public credentialAnchors;
    
    // Events for indexing
    event PropertyRegistered(
        bytes32 indexed propertyDIDHash,
        bytes32 titleVCHash,
        uint256 timestamp
    );
    
    event OwnershipTransferred(
        bytes32 indexed propertyDIDHash,
        bytes32 oldOwnerDIDHash,
        bytes32 newOwnerDIDHash,
        bytes32 transferVCHash,
        uint256 timestamp
    );
    
    event CredentialAnchored(
        bytes32 indexed credentialHash,
        address indexed issuer,
        uint256 timestamp
    );
    
    /**
     * @notice Register a new property in the system
     * @param propertyDIDHash Hash of the property's DID
     * @param titleVCHash Hash of the PropertyTitleVC
     * @param ownerDIDHash Hash of the current owner's DID
     */
    function registerProperty(
        bytes32 propertyDIDHash,
        bytes32 titleVCHash,
        bytes32 ownerDIDHash
    ) external {
        require(!properties[propertyDIDHash].isActive, "Property already registered");
        
        properties[propertyDIDHash] = PropertyAnchor({
            currentTitleVCHash: titleVCHash,
            currentOwnerDIDHash: ownerDIDHash,
            lastUpdated: block.timestamp,
            transferCount: 0,
            isActive: true
        });
        
        credentialAnchors[titleVCHash] = block.timestamp;
        
        emit PropertyRegistered(propertyDIDHash, titleVCHash, block.timestamp);
    }
    
    /**
     * @notice Record an ownership transfer
     * @param propertyDIDHash Hash of the property's DID
     * @param newTitleVCHash Hash of the new PropertyTitleVC
     * @param newOwnerDIDHash Hash of the new owner's DID
     * @param transferVCHash Hash of the OwnershipTransferVC
     */
    function recordTransfer(
        bytes32 propertyDIDHash,
        bytes32 newTitleVCHash,
        bytes32 newOwnerDIDHash,
        bytes32 transferVCHash
    ) external {
        PropertyAnchor storage prop = properties[propertyDIDHash];
        require(prop.isActive, "Property not registered");
        
        bytes32 oldOwnerHash = prop.currentOwnerDIDHash;
        
        prop.currentTitleVCHash = newTitleVCHash;
        prop.currentOwnerDIDHash = newOwnerDIDHash;
        prop.lastUpdated = block.timestamp;
        prop.transferCount++;
        
        credentialAnchors[newTitleVCHash] = block.timestamp;
        credentialAnchors[transferVCHash] = block.timestamp;
        
        emit OwnershipTransferred(
            propertyDIDHash,
            oldOwnerHash,
            newOwnerDIDHash,
            transferVCHash,
            block.timestamp
        );
    }
    
    /**
     * @notice Anchor any credential hash (timestamp proof)
     * @param credentialHash Hash of the credential
     */
    function anchorCredential(bytes32 credentialHash) external {
        require(credentialAnchors[credentialHash] == 0, "Already anchored");
        credentialAnchors[credentialHash] = block.timestamp;
        emit CredentialAnchored(credentialHash, msg.sender, block.timestamp);
    }
    
    /**
     * @notice Verify a credential was anchored
     * @param credentialHash Hash to verify
     * @return timestamp When it was anchored (0 if never)
     */
    function verifyAnchor(bytes32 credentialHash) external view returns (uint256) {
        return credentialAnchors[credentialHash];
    }
    
    /**
     * @notice Get property information
     * @param propertyDIDHash Hash of the property's DID
     */
    function getProperty(bytes32 propertyDIDHash) external view returns (
        bytes32 titleVCHash,
        bytes32 ownerDIDHash,
        uint256 lastUpdated,
        uint256 transferCount,
        bool isActive
    ) {
        PropertyAnchor storage prop = properties[propertyDIDHash];
        return (
            prop.currentTitleVCHash,
            prop.currentOwnerDIDHash,
            prop.lastUpdated,
            prop.transferCount,
            prop.isActive
        );
    }
}
