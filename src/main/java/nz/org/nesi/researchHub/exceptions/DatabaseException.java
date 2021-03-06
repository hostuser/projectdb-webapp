package nz.org.nesi.researchHub.exceptions;

import org.springframework.stereotype.Component;

import com.mangofactory.swagger.annotations.ApiError;

/**
 * Project: project_management
 * <p/>
 * Written by: Markus Binsteiner
 * Date: 5/12/13
 * Time: 11:38 AM
 */
@Component
@ApiError(code=500,reason="Database exception")
public class DatabaseException extends RuntimeException {

    private DatabaseException(){
        super();
    }

    public DatabaseException(String s, Exception e) {
        super(s,e);
    }
}
