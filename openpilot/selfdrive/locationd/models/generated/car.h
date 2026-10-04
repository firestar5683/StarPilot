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
void car_err_fun(double *nom_x, double *delta_x, double *out_4009510058988412331);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_211208841364349865);
void car_H_mod_fun(double *state, double *out_8439691916014613669);
void car_f_fun(double *state, double dt, double *out_2756758349190389597);
void car_F_fun(double *state, double dt, double *out_6650625153394168514);
void car_h_25(double *state, double *unused, double *out_5235044060477467306);
void car_H_25(double *state, double *unused, double *out_3510029197804907996);
void car_h_24(double *state, double *unused, double *out_8680530398976897528);
void car_H_24(double *state, double *unused, double *out_1358785667222798856);
void car_h_30(double *state, double *unused, double *out_8872493588731489656);
void car_H_30(double *state, double *unused, double *out_1017667132322700202);
void car_h_26(double *state, double *unused, double *out_6537464433533729275);
void car_H_26(double *state, double *unused, double *out_231474121069148228);
void car_h_27(double *state, double *unused, double *out_6419457039600352531);
void car_H_27(double *state, double *unused, double *out_1205926938861243015);
void car_h_29(double *state, double *unused, double *out_7182045753995808696);
void car_H_29(double *state, double *unused, double *out_507435788008308018);
void car_h_28(double *state, double *unused, double *out_651026969752255553);
void car_H_28(double *state, double *unused, double *out_5589834805077838592);
void car_h_31(double *state, double *unused, double *out_5089524236256812335);
void car_H_31(double *state, double *unused, double *out_3540675159681868424);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}