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
void car_err_fun(double *nom_x, double *delta_x, double *out_7295323435102138985);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5740214235924271464);
void car_H_mod_fun(double *state, double *out_703782495897250555);
void car_f_fun(double *state, double dt, double *out_4026170021074555431);
void car_F_fun(double *state, double dt, double *out_4652814377482513796);
void car_h_25(double *state, double *unused, double *out_4039743270013067154);
void car_H_25(double *state, double *unused, double *out_4226763145886742232);
void car_h_24(double *state, double *unused, double *out_3606421098967363994);
void car_H_24(double *state, double *unused, double *out_6403977569493892205);
void car_h_30(double *state, double *unused, double *out_4600134206705474730);
void car_H_30(double *state, double *unused, double *out_6745096104393990859);
void car_h_26(double *state, double *unused, double *out_1787582103435621347);
void car_H_26(double *state, double *unused, double *out_485259827012686008);
void car_h_27(double *state, double *unused, double *out_9041416537673912799);
void car_H_27(double *state, double *unused, double *out_8968690175577934076);
void car_h_29(double *state, double *unused, double *out_5767878007781616467);
void car_H_29(double *state, double *unused, double *out_7255327448708383043);
void car_h_28(double *state, double *unused, double *out_5400909299850363481);
void car_H_28(double *state, double *unused, double *out_2172928431638852469);
void car_h_31(double *state, double *unused, double *out_3764549207728561265);
void car_H_31(double *state, double *unused, double *out_4257409107763702660);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}