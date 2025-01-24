set_target_properties(${library_name} PROPERTIES
    AUTOMOC_EXECUTABLE "${CMAKE_SOURCE_DIR}/moc.sh"
    AUTORCC_EXECUTABLE "${CMAKE_SOURCE_DIR}/rcc.sh"
)