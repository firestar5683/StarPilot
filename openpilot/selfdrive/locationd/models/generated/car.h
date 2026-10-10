#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_3194710944048673507);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8039664853018696099);
void car_H_mod_fun(double *state, double *out_5587385678613239193);
void car_f_fun(double *state, double dt, double *out_7292828168458319052);
void car_F_fun(double *state, double dt, double *out_2978169847506375272);
void car_h_25(double *state, double *unused, double *out_4652885364343750448);
void car_H_25(double *state, double *unused, double *out_1635374662770778876);
void car_h_24(double *state, double *unused, double *out_1850369176656129099);
void car_H_24(double *state, double *unused, double *out_537274936234720690);
void car_h_30(double *state, double *unused, double *out_3986992112374791436);
void car_H_30(double *state, double *unused, double *out_4153707621278027503);
void car_h_26(double *state, double *unused, double *out_3448151322053909377);
void car_H_26(double *state, double *unused, double *out_4939900632531579477);
void car_h_27(double *state, double *unused, double *out_4773315296925324726);
void car_H_27(double *state, double *unused, double *out_6377301692461970720);
void car_h_29(double *state, double *unused, double *out_4930501965276453871);
void car_H_29(double *state, double *unused, double *out_4663938965592419687);
void car_h_28(double *state, double *unused, double *out_7810101348369657411);
void car_H_28(double *state, double *unused, double *out_418460051477110887);
void car_h_31(double *state, double *unused, double *out_9129956871281942907);
void car_H_31(double *state, double *unused, double *out_2732336758336628824);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}