package nz.org.nesi.researchHub.exceptions;

import org.springframework.stereotype.Component;

import com.mangofactory.swagger.annotations.ApiError;

/**
 * Project: project_management
 * <p/>
 * Written by: Markus Binsteiner
 * Date: 6/12/13
 * Time: 9:31 AM
 */
@Component
@ApiError(code=500,reason="No such entity in the database")
public class NoSuchEntityException extends Exception {

    private Class entityClass;
    private Integer id;

    public NoSuchEntityException() {
        super();
    }

    public NoSuchEntityException(String msg, Class entityClass, Integer id) {
        super(msg);
        this.entityClass = entityClass;
        this.id = id;
    }

    public Class getEntityClass() {
        return entityClass;
    }

    public void setEntityClass(Class entityClass) {
        this.entityClass = entityClass;
    }

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }
}
